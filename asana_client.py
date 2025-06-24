import os
import requests
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AsanaClient:
    """
    V4: An adapter class to handle all communications with the Asana API.
    Now includes project searching and proactive task creation.
    """
    API_BASE_URL = "https://app.asana.com/api/1.0"

    def __init__(self):
        """
        Initializes the Asana client and the requests session.
        """
        self.session = None
        self.workspace_gid = os.environ.get("ASANA_WORKSPACE_GID")
        try:
            token = os.environ.get('ASANA_PERSONAL_ACCESS_TOKEN')
            if not token or not self.workspace_gid:
                raise ValueError("Asana token or workspace GID not set in .env file.")

            self.session = requests.Session()
            self.session.headers.update({"Authorization": f"Bearer {token}", "Accept": "application/json"})

            # Verify credentials
            response = self.session.get(f"{self.API_BASE_URL}/users/me")
            response.raise_for_status()
            logging.info("ASANA CLIENT: Initialized and token verified successfully.")

        except Exception as e:
            logging.error(f"ASANA CLIENT ERROR: Failed to initialize - {e}")
            self.session = None

    def find_project_by_name(self, project_name: str) -> str | None:
        """
        Finds a project's GID within the configured workspace by its name.
        """
        if not self.session: return None
        logging.info(f"ASANA CLIENT: Searching for project named '{project_name}'...")

        url = f"{self.API_BASE_URL}/projects"
        params = {"workspace": self.workspace_gid, "opt_fields": "name"}

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            projects = response.json().get('data', [])

            for project in projects:
                if project.get('name', '').lower() == project_name.lower():
                    logging.info(f"ASANA CLIENT: Found project '{project_name}' with GID: {project['gid']}")
                    return project['gid']

            logging.warning(f"ASANA CLIENT: Project '{project_name}' not found.")
            return None
        except Exception as e:
            logging.error(f"ASANA CLIENT ERROR: Failed to find project '{project_name}': {e}")
            return None

    def create_task_with_attachment(self, project_gid: str, task_name: str, transcript_content: str) -> str | None:
        """
        Creates a new task in a specified project and attaches the transcript.
        """
        if not self.session: return None
        logging.info(f"ASANA CLIENT: Creating task '{task_name}' in project {project_gid}...")

        try:
            # Step 1: Create the task
            task_url = f"{self.API_BASE_URL}/tasks"
            task_payload = {"data": {"name": task_name, "workspace": self.workspace_gid, "projects": [project_gid]}}
            self.session.headers.update({"Content-Type": "application/json"})
            response = self.session.post(task_url, json=task_payload)
            response.raise_for_status()
            new_task_gid = response.json().get('data', {}).get('gid')
            if not new_task_gid: raise Exception("Failed to get GID from new task response.")
            logging.info(f"ASANA CLIENT: Successfully created task with GID: {new_task_gid}")

            # Step 2: Attach the transcript
            attach_url = f"{self.API_BASE_URL}/tasks/{new_task_gid}/attachments"
            if "Content-Type" in self.session.headers: del self.session.headers["Content-Type"]
            files = {'file': ('transcript.txt', transcript_content, 'text/plain')}
            response = self.session.post(attach_url, files=files)
            response.raise_for_status()
            logging.info(f"ASANA CLIENT: Successfully attached transcript.")

            return new_task_gid
        except Exception as e:
            logging.error(f"ASANA CLIENT ERROR: Failed to create task with attachment: {e}")
            return None

    def post_comment_to_task(self, task_gid: str, comment_html: str):
        """
        Posts a rich text comment to a specific Asana task.
        """
        # (Implementation is the same as V3)
        if not self.session: return
        logging.info(f"ASANA CLIENT: Posting comment to task {task_gid}...")
        try:
            url = f"{self.API_BASE_URL}/tasks/{task_gid}/stories"
            self.session.headers.update({"Content-Type": "application/json"})
            payload = {"data": {"html_text": f"<body>{comment_html}</body>"}}
            self.session.post(url, json=payload).raise_for_status()
            logging.info(f"ASANA CLIENT: Successfully posted comment.")
        except Exception as e:
            logging.error(f"ASANA CLIENT ERROR: Failed to post comment: {e}")

    def create_subtask(self, parent_task_gid: str, subtask_name: str, due_on: str | None = None):
        """
        Creates a new sub-task with an optional due date.
        """
        # (Implementation is the same as V3)
        if not self.session: return
        logging.info(f"ASANA CLIENT: Creating sub-task '{subtask_name}'...")
        try:
            url = f"{self.API_BASE_URL}/tasks"
            self.session.headers.update({"Content-Type": "application/json"})
            payload_data = {"name": subtask_name, "parent": parent_task_gid}
            if due_on: payload_data['due_on'] = due_on
            self.session.post(url, json={"data": payload_data}).raise_for_status()
            logging.info(f"ASANA CLIENT: Successfully created sub-task.")
        except Exception as e:
            logging.error(f"ASANA CLIENT ERROR: Failed to create sub-task: {e}")
