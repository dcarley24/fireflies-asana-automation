import os
import requests
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class FirefliesClient:
    """
    V4.4: An adapter class to handle all communications with the Fireflies.ai GraphQL API
    using the requests library directly.
    """
    API_URL = "https://api.fireflies.ai/graphql"

    def __init__(self):
        """
        Initializes the client by setting up the API key for the authorization header.
        """
        self.api_key = os.environ.get('FIREFLIES_API_KEY')
        if not self.api_key or self.api_key == '<Your Fireflies API Key Here>':
            logging.error("FIREFLIES CLIENT ERROR: FIREFLIES_API_KEY not found or not set in .env file.")
            self.api_key = None
        else:
            logging.info("FIREFLIES CLIENT: Initialized successfully.")

    def get_transcript_and_title(self, meeting_id: str) -> dict | None:
        """
        V4.4 UPDATE: Fetches both the transcript and the title from Fireflies.

        Args:
            meeting_id: The unique ID of the meeting from Fireflies.

        Returns:
            A dictionary containing the 'transcript' and 'title', or None if an error occurs.
            e.g., {'transcript': '...', 'title': '...'}
        """
        if not self.api_key:
            logging.error("FIREFLIES CLIENT ERROR: Client not initialized. Cannot get data.")
            return None

        logging.info(f"FIREFLIES CLIENT: Fetching transcript and title for meeting ID: {meeting_id} via GraphQL...")

        # V4.4 UPDATE: The GraphQL query now also asks for the meeting title.
        graphql_query = """
            query GetTranscript($id: String!) {
                transcript(id: $id) {
                    title
                    sentences {
                        speaker_name
                        text
                    }
                }
            }
        """

        payload = { "query": graphql_query, "variables": { "id": meeting_id } }
        headers = { "Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json" }

        try:
            response = requests.post(self.API_URL, headers=headers, json=payload)
            response.raise_for_status()

            data = response.json()
            transcript_data = data.get('data', {}).get('transcript')

            if not transcript_data:
                logging.warning(f"FIREFLIES CLIENT: No transcript data found for meeting ID: {meeting_id}")
                return None

            sentences = transcript_data.get('sentences')
            title = transcript_data.get('title', 'Untitled Meeting')

            if not sentences:
                logging.warning(f"FIREFLIES CLIENT: No sentences found in transcript for meeting ID: {meeting_id}")
                return None

            full_transcript_parts = [f"{sentence.get('speaker_name', 'Unknown')}: {sentence.get('text', '')}" for sentence in sentences]
            full_transcript = "\n".join(full_transcript_parts)

            logging.info(f"FIREFLIES CLIENT: Successfully fetched data for meeting: '{title}'")
            return {'transcript': full_transcript, 'title': title}

        except requests.exceptions.HTTPError as http_err:
            logging.error(f"FIREFLIES CLIENT HTTP ERROR: {http_err} - Response: {response.text}")
            return None
        except Exception as e:
            logging.error(f"FIREFLIES CLIENT ERROR: An unexpected error occurred: {e}")
            return None
