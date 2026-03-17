import logging
import os
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def get_authenticated_service():
    """
    Authenticates the user and returns the YouTube Data API service instance.
    Utilizes token.json for headless token refreshes on subsequent runs.
    """
    creds = None
    token_file = "token.json"
    secrets_file = "client_secrets.json"

    if os.path.exists(token_file):
        logging.info("Loading existing credentials from token.json.")
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logging.info("Refreshing expired access token.")
            creds.refresh(Request())
        else:
            if not os.path.exists(secrets_file):
                logging.error(f"Missing {secrets_file}. Cannot perform initial OAuth flow.")
                sys.exit(1)
            logging.info("Initiating local server for initial OAuth authorization.")
            flow = InstalledAppFlow.from_client_secrets_file(secrets_file, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_file, "w") as token:
            token.write(creds.to_json())
            logging.info("Saved new credentials to token.json.")

    return build("youtube", "v3", credentials=creds)

def upload_video(
    youtube,
    file_path: str,
    title: str,
    description: str,
    category_id: str = "27",
    tags: list[str] = None,
) -> None:
    """
    Uploads the video file to the authenticated YouTube channel.
    Category 27 maps to 'Education'.
    """
    if tags is None:
        tags = ["Science", "Engineering", "History", "Shorts"]

    logging.info(f"Preparing upload for: {file_path}")
    
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        file_path,
        mimetype="video/mp4",
        resumable=True,
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    logging.info("Executing video upload. This may take a few minutes.")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            logging.info(f"Upload progress: {int(status.progress() * 100)}%")

    logging.info(f"Upload complete. Video ID: {response.get('id')}")

if __name__ == "__main__":
    logging.info("Starting manual OAuth initialization.")
    youtube_service = get_authenticated_service()
    logging.info("Initialization complete. The pipeline is ready for headless execution.")
