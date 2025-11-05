#!/bin/bash

# XTTS Streaming API Startup Script

export COQUI_TOS_AGREED=1

echo "Starting XTTS Streaming API..."
echo "Make sure you have installed requirements: pip install -r requirements.txt"
echo ""

# Run with uvicorn
uvicorn app:app --host 0.0.0.0 --port 8001 --workers 1