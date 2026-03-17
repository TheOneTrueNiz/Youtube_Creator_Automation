# YouTube Creator Automation Pipeline

An automated Python pipeline designed to generate engaging, high-fidelity short-form videos for YouTube Shorts and Facebook Reels.

The pipeline leverages Google Cloud Vertex AI (Gemini, Veo 3.1, Imagen 3.0) and Cloud Text-to-Speech to generate all media assets headlessly. It uses local FFmpeg for assembly and includes browser automation via Playwright for Facebook Reels uploads.

## Features

- **Brain:** Gemini 2.5 Flash generates unique daily scripts and media prompts.
- **Video Hook:** Veo 3.1 generates a cinematic 8-second 9:16 vertical video hook.
- **Image Fill:** Imagen 3.0 generates high-quality vertical visuals to complete the timeline.
- **Narration:** Google Cloud TTS (Journey voice) for human-like narration.
- **Subtitles:** Local OpenAI Whisper model for accurate SRT generation.
- **Assembly:** Dynamic FFmpeg engine with Ken Burns effects, crossfades, and ambient background music.
- **Multi-Platform:** Automated publishing to YouTube and Facebook Reels.

## Prerequisites

- **Python 3.10+**
- **FFmpeg** installed in system PATH.
- **Google Cloud Project** with Vertex AI and Cloud TTS enabled.

---

## Detailed Configuration Guide

### 1. Google Cloud / Vertex AI / YouTube
To use the automated generation and YouTube uploading features, you must configure a Google Cloud Project:

1.  **Create a GCP Project:** Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a new project.
2.  **Enable APIs:** In the "APIs & Services" dashboard, enable the following:
    *   **Vertex AI API** (Required for Gemini, Veo, and Imagen)
    *   **Cloud Text-to-Speech API** (Required for narration)
    *   **YouTube Data API v3** (Required for uploading)
3.  **Application Default Credentials (ADC):**
    Install the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) and run:
    ```bash
    gcloud auth application-default login
    ```
    This allows `main.py` to authenticate with Vertex AI and TTS services.
4.  **YouTube OAuth Credentials:**
    *   Go to **APIs & Services > Credentials**.
    *   Click **Create Credentials > OAuth client ID**.
    *   Select **Desktop App** as the application type.
    *   Download the JSON file and rename it to `client_secrets.json` in the project root.
    *   **Initial Run:** Execute `python youtube_uploader.py`. This will open a browser for a one-time manual authorization. It generates `token.json`, which the pipeline uses for headless uploads thereafter.

### 2. Facebook Reels (Meta)
The pipeline uses **Playwright** browser automation to upload Reels, as the official Meta Graph API for Reels is highly restricted.

1.  **Initial Authentication:**
    *   The first time the pipeline runs (or if you run `python meta_uploader.py` directly), Playwright will launch a browser.
    *   If no session is found, it will pause and prompt you in the terminal to log in to Facebook manually in the opened browser window.
    *   After logging in and reaching the home page, press **Enter** in your terminal.
2.  **Session Persistence:**
    *   The pipeline saves your login state to `fb_state.json`.
    *   Subsequent runs will use this file to upload headlessly without requiring manual intervention.
    *   **Note:** If `fb_state.json` expires or the upload fails due to a login wall, simply delete `fb_state.json` and run the pipeline again to re-authenticate.

### 3. Audio Library
*   Add your `.mp3` or `.wav` background tracks to the `audio_library/` directory. 
*   The pipeline selects one at random for each video and mixes it with the narration at a lower volume.

---

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd Youtube_Creator_Automation

# Install dependencies (recommended to use a venv)
python -m venv venv
source venv/bin/activate
pip install .
playwright install chromium
```

## Running the Pipeline

### Manual Execution
```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
python main.py
```

### Automated Execution (Linux/Systemd)
Use the provided deployment script to schedule the pipeline daily at 3:00 AM:
```bash
./deploy_systemd.sh your-project-id
```

## Project Structure

- `main.py`: The central orchestrator.
- `youtube_uploader.py`: YouTube Data API integration & OAuth manager.
- `meta_uploader.py`: Facebook Reels browser automation via Playwright.
- `ledger.py`: SQLite-based history to avoid duplicate topics.
- `audio_library/`: Directory for background music assets.
- `output/`: Temporary directory for generated media.

## License
MIT
