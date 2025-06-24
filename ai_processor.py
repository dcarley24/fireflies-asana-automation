import os
import json
import logging
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging (set to DEBUG temporarily for detailed tracing)
# For production, consider setting this back to INFO or WARNING.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger().setLevel(logging.DEBUG) # Temporarily set root logger to DEBUG

# --- Google AI Setup ---
try:
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables.")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    logging.info("AI PROCESSOR: Google AI model ('gemini-1.5-flash-latest') initialized successfully.")
except Exception as e:
    logging.error(f"AI PROCESSOR ERROR: Failed to configure Google AI - {e}")
    model = None

def classify_meeting(transcript: str) -> dict:
    """
    Pass 0: The "Meeting Classifier"
    Analyzes the transcript to determine meeting type and client name for routing.
    """
    logging.info("AI PROCESSOR: Starting Pass 0 - Classifying meeting...")
    logging.debug(f"DEBUG_P0: Input transcript (first 500 chars): {transcript[:500]}")
    if not model: return {}

    prompt = f"""
    You are a Meeting Classifier. Your task is to analyze the start of a meeting transcript to determine two things: the meeting_type and the client_name.

    - `meeting_type`: Must be either "internal" or "external".
    - `client_name`: If the meeting is external, identify the client's company name. If internal or not mentioned, use "N/A".
    - IMPORTANT: If `meeting_type` is 'internal', `client_name` MUST be 'N/A'. Only extract a `client_name` if `meeting_type` is 'external' AND an external company is clearly mentioned as the meeting's primary subject.

    **Output Format:** Your response MUST be a single, valid JSON object and nothing else.

    Here is the transcript:
    ---
    {transcript[:1500]}
    ---
    """

    generation_config = genai.types.GenerationConfig(response_mime_type="application/json")
    try:
        response = model.generate_content(prompt, generation_config=generation_config)
        logging.debug(f"DEBUG_P0: Raw AI response text: {response.text}")
        classification = json.loads(response.text)
        logging.debug(f"DEBUG_P0: Parsed classification: {json.dumps(classification, indent=2)}")
        logging.info(f"AI PROCESSOR: Pass 0 Complete. Classification: {classification}")
        return classification
    except Exception as e:
        logging.error(f"AI PROCESSOR ERROR: An error occurred during meeting classification: {e}")
        return {}

def clean_transcript(raw_text: str) -> str:
    """
    Pass 1: The "Meticulous Editor"
    Cleans up the raw transcript by correcting typos and removing filler words.
    """
    logging.info("AI PROCESSOR: Starting Pass 1 - Cleaning transcript...")
    logging.debug(f"DEBUG_P1: Input raw text (first 500 chars): {raw_text[:500]}")
    if not model: return raw_text
    prompt = f"""
    You are a Meticulous Editor. Your only task is to process a raw, noisy meeting transcript and clean it for clarity.
    Follow these instructions precisely:
    1.  Correct Obvious Typos.
    2.  Remove Filler Words (e.g., "um," "uh," "like," "you know").
    3.  Do Not Summarize or alter the meaning of the sentences.
    4.  IMPORTANT: Only use content from the provided transcript. Do not add any outside information.

    Here is the raw transcript to clean:
    ---
    {raw_text}
    ---
    """
    try:
        response = model.generate_content(prompt)
        logging.debug(f"DEBUG_P1: Output cleaned text (first 500 chars): {response.text[:500]}")
        logging.info("AI PROCESSOR: Pass 1 Complete.")
        return response.text
    except Exception as e:
        logging.error(f"AI PROCESSOR ERROR: An error occurred during transcript cleaning: {e}")
        return raw_text

def extract_structured_data(cleaned_transcript: str) -> dict:
    """
    Pass 2: The "Business Analyst"
    Extracts key decisions, action items, and unanswered questions into a structured JSON format.
    Includes an 'empty_data' flag if no meaningful data is found.
    """
    logging.info("AI PROCESSOR: Starting Pass 2 - Extracting structured data...")
    logging.debug(f"DEBUG_P2: Input cleaned transcript (first 500 chars): {cleaned_transcript[:500]}")
    if not model: return {}

    prompt = f"""
    You are a data extraction robot. Your only job is to read a transcript and extract specific pieces of information into a valid JSON object. Do not add any conversational text or explanations.

    **Instructions:**
    1. Read the transcript provided below.
    2. Extract the following information:
      - `client_name`: The name of the client or project. If not mentioned, use "Unknown".
      - `key_decisions`: A list of all significant decisions made during the meeting.
      - `action_items`: A list of all tasks assigned. Each item must be an object with `owner`, `task`, and `due_date`. For the `due_date`, use the formatYYYY-MM-DD if possible.
      - `unanswered_questions`: A list of questions that were raised but not answered.
    3. If a piece of information is not present, use an empty list `[]` or an appropriate default (like "N/A" for strings).
    4. IMPORTANT: If `key_decisions`, `action_items`, AND `unanswered_questions` are all empty lists, AND `client_name` is "Unknown" or "N/A", ALSO include a key `"empty_data": true` in the top-level JSON object. Otherwise, omit this key.
    5. Your final output must only be the JSON object.
    6. IMPORTANT: Only use content from the provided transcript. Do not use any outside knowledge or make up any information. If the answer is not in the text, provide an empty list or "N/A".

    **Example Output Format (with data):**
    ```json
    {{
      "client_name": "Example Corp",
      "key_decisions": [
        "The team will proceed with Option A for the main feature.",
        "The project deadline is confirmed for next quarter."
      ],
      "action_items": [
        {{
          "owner": "Sarah",
          "task": "Update the project roadmap",
          "due_date": "2025-07-01"
        }}
      ],
      "unanswered_questions": [],
      "empty_data": false
    }}
    ```

    **Example Output Format (for empty data):**
    ```json
    {{
      "client_name": "N/A",
      "key_decisions": [],
      "action_items": [],
      "unanswered_questions": [],
      "empty_data": true
    }}
    ```

    Here is the cleaned transcript:
    ---
    {cleaned_transcript}
    ---
    """

    generation_config = genai.types.GenerationConfig(response_mime_type="application/json")
    try:
        response = model.generate_content(prompt, generation_config=generation_config)
        logging.debug(f"DEBUG_P2: Raw AI response text from generate_content: {response.text}") # CRITICAL DEBUG PRINT
        data = json.loads(response.text)
        logging.debug(f"DEBUG_P2: Parsed structured data: {json.dumps(data, indent=2)}")

        # Safety check: Ensure empty_data flag is correctly set even if AI misses it
        if not data.get('client_name') or data['client_name'].upper() in ["UNKNOWN", "N/A"]:
            if not data.get('key_decisions') and not data.get('action_items') and not data.get('unanswered_questions'):
                data['empty_data'] = True
        else:
            data['empty_data'] = data.get('empty_data', False) # Default to false if not explicitly true

        logging.info("AI PROCESSOR: Pass 2 Complete.")
        return data
    except json.JSONDecodeError as e:
        logging.error(f"AI PROCESSOR ERROR: JSON decoding failed for Pass 2 output: {e}. Raw response: {response.text}")
        return {"empty_data": True, "error": str(e)} # Return empty flag on error
    except Exception as e:
        logging.error(f"AI PROCESSOR ERROR: An error occurred during data extraction: {e}")
        return {"empty_data": True, "error": str(e)} # Return empty flag on error

def write_project_brief(structured_data: dict) -> str:
    """
    Pass 3: The "Project Brief Writer"
    Generates a markdown-formatted project brief from the structured data.
    This function will now expect to be called only if meaningful data is present,
    or it will generate a generic "no data" brief.
    """
    logging.info("AI PROCESSOR: Starting Pass 3 - Writing project brief...")
    logging.debug(f"DEBUG_P3: Input structured_data: {json.dumps(structured_data, indent=2)}")

    # Check if we have effectively empty data (e.g., from an error or no extraction)
    if not structured_data or structured_data.get("empty_data", False):
        logging.info("AI PROCESSOR: Generating concise 'no data' brief.")
        # Reverting to HTML strong for robust bolding, and h2 for heading
        return """
<h2><strong>Meeting Summary</strong></h2>

This meeting did not contain explicit key decisions, action items, or unanswered questions that could be automatically extracted.

Please review the full transcript for context or if you were expecting specific outcomes.
"""

    client_name = structured_data.get('client_name', 'Unknown Project')
    # Reverting to HTML h2 for main heading and strong for bolding
    brief_parts = [f"<h2><strong>Project Brief: {client_name}</strong></h2>"]

    key_decisions = structured_data.get('key_decisions', [])
    if key_decisions:
        brief_parts.append("<strong>Key Decisions:</strong>")
        brief_parts.append("<ul>")
        brief_parts.extend([f"<li>{item}</li>" for item in key_decisions])
        brief_parts.append("</ul>")

    action_items = structured_data.get('action_items', [])
    if action_items:
        brief_parts.append("<strong>Action Items (Sub-tasks to be created automatically):</strong>")
        brief_parts.append("<ul>")
        brief_parts.extend([
            f"<li><strong>{item.get('task', 'N/A')}</strong> (Owner: {item.get('owner', 'N/A')}, Due: {item.get('due_date', 'N/A')})</li>"
            for item in action_items
        ])
        brief_parts.append("</ul>")

    unanswered_questions = structured_data.get('unanswered_questions', [])
    if unanswered_questions:
        brief_parts.append("<strong>Open Questions:</strong>")
        brief_parts.append("<ul>")
        brief_parts.extend([f"<li>{item}</li>" for item in unanswered_questions])
        brief_parts.append("</ul>")

    logging.info("AI PROCESSOR: Pass 3 Complete.")
    return "\n".join(brief_parts) # Join with newlines for cleaner HTML structure
