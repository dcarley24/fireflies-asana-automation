# Fireflies-Asana Automation

This project is an intelligent, event-driven service designed to automate the workflow between [Fireflies.ai](https://fireflies.ai) and [Asana](https://asana.com). It listens for completed meeting transcriptions from Fireflies, uses a multi-pass AI workflow to classify, clean, analyze, and summarize the content, and then automatically creates a structured, actionable project brief within the correct Asana project, complete with an assignable sub-task for every action item identified in the meeting.

The primary goal is to eliminate the manual work of processing meeting notes, creating a "zero-touch" bridge from conversation to action.

## Why This Project Exists: The Limitations of the Native Integration
While Fireflies.ai offers a native integration with Asana, it is insufficient for most dynamic, multi-client workflows. The out-of-the-box solution suffers from critical limitations:

* **Static Configuration:** The native integration can only be configured to send tasks to a single, predefined Asana project and a single list within that project. This makes it unworkable for teams that handle multiple projects or clients, as it would require constant manual reconfiguration.

* **Broad, Non-Actionable Tasks:** The integration typically creates broad tasks for the entire meeting (e.g., "Attend meeting about Project X"). It lacks the intelligence to parse the conversation and identify the discrete, actionable tasks that were actually agreed upon.

This project was built to solve these specific problems. It replaces the rigid, native integration with an intelligent, "zero-touch" automation layer. Instead of just creating generic tasks, our multi-pass AI engine actively listens to the conversation, understands its context, identifies the truly actionable tasks, and routes a complete, structured brief to the correct Asana project, turning raw conversation into organized work automatically.

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

### Running Locally for Development

1.  **Start the Flask Server:**
    From the project's root directory, run the application.
    ```bash
    python app.py
    ```
    The server will start on `http://localhost:5019`. The `/webhook/fireflies` endpoint will be available for local testing.

### Deployment for Live Webhooks

For the application to receive live webhook notifications from Fireflies.ai, it must be deployed to a hosting service that provides a stable, public URL (e.g., Render, Heroku, AWS).

1.  Deploy the application to your chosen hosting provider.
2.  Once deployed, you will have a public URL for the service (e.g., `https://your-app-name.onrender.com`).
3.  Go to your Fireflies.ai developer settings and configure the webhook to point to your public URL's webhook endpoint: `https://<your-public-app-url>/webhook/fireflies`.

## Testing the Webhook Locally

You can test the entire workflow without deploying the application by sending a simulated webhook request to your local running server using `curl`. This is the recommended way to test changes during development.

1.  Get a valid Meeting ID from a past meeting in your Fireflies account.
2.  Run the following command in a terminal, replacing the placeholder values with your real data. This command sends the request directly to your local server.

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
