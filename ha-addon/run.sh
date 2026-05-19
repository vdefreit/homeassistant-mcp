#!/bin/sh
echo "Starting AI Automation Assistant v1.0.0"
cd /app
exec uvicorn app.main:app --host 0.0.0.0 --port 8099
