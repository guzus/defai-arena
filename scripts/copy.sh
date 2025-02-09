#!/usr/bin/env bash
set -e

# Load environment variables from the .env file if it exists
if [ -f "server.env" ]; then
  set -a  # Automatically export variables loaded from the .env file
  . ./server.env
  set +a
fi

# Use default values if specific variables are not set in the .env file
SSH_FILE="${SSH_FILE}"
SERVER_USER="${SERVER_USER}"
SERVER_IP="${SERVER_IP}"
REMOTE_DIR="${REMOTE_DIR}"
PROJECT_DIR="${PROJECT_DIR}"


rsync -av --filter=":- .gitignore" -e "ssh -i $SSH_FILE" . "$SERVER_USER@$SERVER_IP:$REMOTE_DIR/$PROJECT_DIR"