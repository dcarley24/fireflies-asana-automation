# Fireflies-Asana Automation

This project is an intelligent, event-driven service designed to automate the workflow between [Fireflies.ai](https://fireflies.ai) and [Asana](https://asana.com). It listens for completed meeting transcriptions from Fireflies, uses a multi-pass AI workflow to clean, analyze, and summarize the content, and then automatically creates a structured, actionable project brief within the correct Asana project.

The primary goal is to eliminate the manual work of processing meeting notes, creating a "zero-touch" bridge from conversation to action.

## Core Features

* **Automated Triggering:** The entire workflow is initiated automatically via a "Transcription Completed" webhook from Fireflies.ai.
* **Multi-Pass AI Processing:** Leverages a chained AI workflow for high-quality output:
    * **Pass 0 (Classifier):** Intelligently determines if a meeting is internal or external and identifies the client to enable project routing.
    * **Pass 1 (Editor):** Cleans the raw transcript, correcting typos and removing filler words.
    * **Pass 2 (Analyst):** Extracts structured data like key decisions, action items, and open questions into a JSON format.
    * **Pass 3 (Writer):** Composes a professional, well-formatted project brief from the structured data.
* **Intelligent Asana Routing:** Automatically finds the correct client-specific project in Asana or falls back to a default "intake" project if one isn't found.
* **Automated Sub-task Creation:** Creates an assignable Asana sub-task for every action item identified in the meeting.
* **Secure Webhook Handling:** Uses a shared secret to verify that all incoming webhook requests are legitimate.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

* Python 3.10+
* `pip` for installing Python packages
* `ngrok` for exposing the local server to the internet for webhook testing.

### Installation

1.  **Clone the repository:**
    ```bash
    git clone git@github.com:dcarley24/fireflies-asana-automation.git
    cd fireflies-asana-automation
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install the required packages:**
    ```bash
    pip install -r requirements.txt
    ```

### Configuration

1.  **Create a `.env` file:**
    Make a copy of the example environment file.
    ```bash
    cp .env.example .env
    ```

2.  **Edit the `.env` file** and fill in the values for the following keys:
    * `ASANA_PERSONAL_ACCESS_TOKEN`: Your Personal Access Token from the Asana Developer Console.
    * `ASANA_WORKSPACE_GID`: The GID of your main Asana workspace.
    * `ASANA_PROJECT_GID`: The GID of your default project where summaries should be created if a client-specific project isn't found.
    * `FIREFLIES_API_KEY`: Your API key from your Fireflies.ai account settings.
    * `FIREFLIES_WEBHOOK_SECRET`: A long, random string you create. You will use this same secret when configuring the webhook in Fireflies.
    * `GOOGLE_API_KEY`: Your API key for the Gemini model from Google AI Studio.

## Running the Application

1.  **Start the Flask Server:**
    From the project's root directory, run the application.
    ```bash
    python app.py
    ```
    The server will start on `http://0.0.0.0:5019`.

2.  **Expose the Server with `ngrok`:**
    In a new terminal window, start `ngrok` to create a public URL that forwards to your local server.
    ```bash
    ngrok http 5019
    ```ngrok` will provide you with a public URL (e.g., `https://random-string.ngrok-free.app`).

3.  **Configure the Fireflies Webhook:**
    * Log in to your Fireflies.ai account and navigate to your API/Integrations settings.
    * Create a new webhook for the "Transcription Completed" event.
    * **Secret key:** Paste the same `FIREFLIES_WEBHOOK_SECRET` value from your `.env` file.
    * Save and enable the webhook.

## Testing

You can test the entire workflow without waiting for a new meeting by simulating the Fireflies webhook with `curl`.

1.  Get a valid Meeting ID from a past meeting in your Fireflies account.
2.  Run the following command in a terminal, replacing the placeholder values.
    ```bash
    curl -X POST http://localhost:5019/webhook/fireflies \
    -H "Content-Type: application/json" \
    -H "fireflies-webhook-secret: <YOUR_WEBHOOK_SECRET_HERE>" \
    -d '{
        "id": "<YOUR_REAL_MEETING_ID_HERE>",
        "title": "Manual Test Meeting"
    }'
    ```
This will trigger the application, and you can monitor the log output in your Flask server's terminal to see the process unfold.
