import os
import logging
from flask import Flask, request, jsonify, abort
from dotenv import load_dotenv

# Import V4 custom modules
from fireflies_client import FirefliesClient
from asana_client import AsanaClient
import ai_processor

# Load environment variables from .env file
load_dotenv()

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# Temporarily set root logger to DEBUG for more detailed tracing during development
# For production, consider setting this back to logging.INFO or logging.WARNING.
logging.getLogger().setLevel(logging.DEBUG)

def create_app():
    """
    V4: Factory function to create and configure the Flask application.
    """
    app = Flask(__name__)

    # Initialize clients
    # Note: FirefliesClient and AsanaClient should be initialized here
    # and passed configurations/API keys if not using global singletons.
    # For this example, assuming they handle their own config via env vars.
    fireflies_client = FirefliesClient()
    asana_client = AsanaClient()

    ASANA_DEFAULT_PROJECT_GID = os.environ.get("ASANA_PROJECT_GID")
    FIREFLIES_WEBHOOK_SECRET = os.environ.get("FIREFLIES_WEBHOOK_SECRET")

    @app.route('/webhook/fireflies', methods=['POST'])
    def fireflies_webhook():
        """
        V4: This is the main entry point, triggered by Fireflies.ai when a transcript is ready.
        """
        logging.info("V4 WEBHOOK: Received POST notification from Fireflies.")

        # --- Webhook Secret Verification (Security Check) ---
        if FIREFLIES_WEBHOOK_SECRET:
            signature = request.headers.get('fireflies-webhook-secret')
            if signature != FIREFLIES_WEBHOOK_SECRET:
                logging.warning("Unauthorized webhook attempt: Invalid secret.")
                abort(401, "Invalid webhook secret.")
            logging.info("Webhook secret verified successfully.")
        else:
            logging.warning("FIREFLIES_WEBHOOK_SECRET not set. Webhook verification skipped.")


        if not ASANA_DEFAULT_PROJECT_GID:
            logging.error("Server is not configured. Missing ASANA_PROJECT_GID in .env file.")
            abort(500, "Server configuration error.")

        data = request.json
        # Fireflies webhook payload structure varies.
        # Assuming 'id' is the meeting ID from a 'meeting.completed' event.
        # Adjust 'data.get('id')' based on actual Fireflies webhook docs if needed for other event types.
        meeting_id = data.get('id')
        event_type = data.get('event_type') # Fireflies often sends 'meeting.completed'

        if not meeting_id:
            logging.warning("Received Fireflies webhook with missing meeting ID.")
            return jsonify({"status": "error", "message": "Missing meeting ID in payload"}), 400

        if event_type and event_type != 'meeting.completed':
            logging.info(f"Received Fireflies event of type '{event_type}', but only 'meeting.completed' is processed. Skipping.")
            return jsonify({"status": "skipped", "message": f"Event type '{event_type}' not processed"}), 200


        logging.info(f"Processing Fireflies meeting ID: {meeting_id}")

        # --- Step 1: Fetch meeting data from Fireflies (transcript and title) ---
        meeting_data = fireflies_client.get_transcript_and_title(meeting_id)
        if not meeting_data or not meeting_data.get('transcript'):
            logging.error(f"Failed to fetch transcript for meeting ID: {meeting_id}")
            abort(500, f"Could not retrieve transcript data for meeting ID: {meeting_id}")

        transcript = meeting_data.get('transcript')
        meeting_title = meeting_data.get('title', 'Untitled Meeting')

        # --- DEMO SAFE REVERSION: Bypassing AI Classification & Routing ---
        # The following 'classify_meeting' and 'find_project_by_name' logic is temporarily disabled
        # for a predictable demo that always posts to the default project.
        # To re-enable, simply uncomment the following block and ensure AsanaClient has find_project_by_name.
        #
        # classification = ai_processor.classify_meeting(transcript)
        # meeting_type = classification.get('meeting_type', 'internal')
        # client_name = classification.get('client_name', 'N/A')
        #
        # target_project_gid_from_ai = ASANA_DEFAULT_PROJECT_GID
        # if meeting_type == 'external' and client_name != 'N/A':
        #    logging.info(f"External meeting identified. Searching for project for client: {client_name}")
        #    # Assuming asana_client.find_project_by_name exists and works
        #    found_project_gid = asana_client.find_project_by_name(client_name)
        #    if found_project_gid:
        #        target_project_gid_from_ai = found_project_gid
        #    else:
        #        logging.warning(f"Client project for '{client_name}' not found. Using default project.")
        # target_project_gid = target_project_gid_from_ai # Use the dynamically determined GID

        target_project_gid = ASANA_DEFAULT_PROJECT_GID # For predictable demo
        logging.info(f"DEMO MODE: Bypassing AI routing. Using default project GID: {target_project_gid}")
        # --- END DEMO SAFE REVERSION ---

        # --- Step 2: Create a placeholder task in Asana for the brief ---
        task_name = f"Meeting Summary: {meeting_title}"
        new_task_gid = asana_client.create_task_with_attachment(
            project_gid=target_project_gid,
            task_name=task_name,
            transcript_content=transcript # Attach the raw transcript
        )
        if not new_task_gid:
            logging.error("Failed to create the initial task in Asana or attach transcript.")
            abort(500, "Failed to create the initial Asana task.")

        logging.info(f"ASANA CLIENT: Successfully created task with GID: {new_task_gid} and attached transcript.")

        # --- Step 3: AI Processing Pipeline ---
        # Pass 1: Clean Transcript
        cleaned_transcript = ai_processor.clean_transcript(transcript)

        # Pass 2: Extract Structured Data
        structured_data = ai_processor.extract_structured_data(cleaned_transcript)

        # --- MODIFICATION: Graceful handling for empty or malformed structured data ---
        project_brief_content = ""
        action_items_to_create = []

        if not structured_data or not isinstance(structured_data, dict) or structured_data.get("empty_data", False):
            logging.info("AI PROCESSOR: Detected empty or invalid structured data from Pass 2. Generating concise 'no data' brief.")
            # Call write_project_brief with the "empty_data" flag to get the generic message
            project_brief_content = ai_processor.write_project_brief({"empty_data": True})
            # No action items to create if data is empty
        else:
            # Pass 3: Write Project Brief (only if data is meaningful)
            project_brief_content = ai_processor.write_project_brief(structured_data)

            # Prepare action items for sub-task creation
            action_items_to_create = structured_data.get('action_items', [])
            if not isinstance(action_items_to_create, list):
                logging.warning("AI PROCESSOR: 'action_items' was not a list, skipping sub-task creation.")
                action_items_to_create = [] # Ensure it's an empty list if malformed

        # --- Step 4: Post the AI-generated brief as a comment to the Asana task ---
        # project_brief_content will now be Markdown from ai_processor
        asana_client.post_comment_to_task(new_task_gid, project_brief_content)
        logging.info("ASANA CLIENT: Successfully posted comment.")

        # --- Step 5: Create sub-tasks (if action items exist) ---
        if action_items_to_create:
            logging.info(f"Creating {len(action_items_to_create)} sub-tasks...")
            for item in action_items_to_create:
                if isinstance(item, dict):
                    subtask_name = item.get('task')
                    owner_name = item.get('owner') # Assuming AsanaClient can map name to GID
                    due_date = item.get('due_date')

                    if subtask_name: # Only create if subtask name exists
                        asana_client.create_subtask(new_task_gid, subtask_name, owner_name=owner_name, due_on=due_date)
                        logging.info(f"ASANA CLIENT: Created sub-task: {subtask_name}")
                    else:
                        logging.warning(f"Skipping sub-task creation due to missing 'task' name in item: {item}")
                else:
                    logging.warning(f"Skipping sub-task creation for non-dict item: {item}")


        logging.info(f"Successfully completed V4 workflow for meeting ID: {meeting_id}. New Asana Task GID: {new_task_gid}")
        return jsonify({"status": "success", "message": "Workflow completed", "asana_task_gid": new_task_gid}), 200

    return app

if __name__ == '__main__':
    app = create_app()
    # Port is read from environment variable FLASK_RUN_PORT, default to 5019 if not set
    port = int(os.environ.get("FLASK_RUN_PORT", 5019))
    app.run(host='0.0.0.0', port=port, debug=True)
