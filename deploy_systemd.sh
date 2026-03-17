#!/bin/bash

if [ -z "$1" ]; then
    echo "Error: Google Cloud Project ID required."
    echo "Usage: ./deploy_systemd.sh YOUR_GOOGLE_CLOUD_PROJECT_ID"
    exit 1
fi

GCP_PROJECT_ID=$1
PROJECT_DIR=$(pwd)
VENV_DIR="$PROJECT_DIR/venv"
OUTPUT_DIR="$PROJECT_DIR/output"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

mkdir -p "$OUTPUT_DIR"
mkdir -p "$SYSTEMD_USER_DIR"

echo "Initializing Python virtual environment..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

echo "Installing dependencies..."
pip install --upgrade pip
pip install .
playwright install chromium

echo "Starting manual OAuth initialization..."
python3 youtube_uploader.py

echo "Writing systemd service file..."
cat <<EOF > "$SYSTEMD_USER_DIR/youtube-creator-automation.service"
[Unit]
Description=YouTube Creator Automation Pipeline
After=network.target

[Service]
Type=oneshot
WorkingDirectory=$PROJECT_DIR
Environment="GOOGLE_CLOUD_PROJECT=$GCP_PROJECT_ID"
ExecStart=$VENV_DIR/bin/python main.py
StandardOutput=append:$OUTPUT_DIR/systemd_execution.log
StandardError=append:$OUTPUT_DIR/systemd_execution.log
EOF

echo "Writing systemd timer file..."
cat <<EOF > "$SYSTEMD_USER_DIR/youtube-creator-automation.timer"
[Unit]
Description=Timer for YouTube Creator Automation Pipeline

[Timer]
OnCalendar=*-*-* 03:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

echo "Reloading systemd user daemon and enabling timer..."
systemctl --user daemon-reload
systemctl --user enable youtube-creator-automation.timer
systemctl --user start youtube-creator-automation.timer

echo "Deployment complete. The pipeline is scheduled to run daily at 3:00 AM."
echo "You can check the timer status with: systemctl --user list-timers"
