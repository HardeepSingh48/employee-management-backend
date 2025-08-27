#!/bin/bash

# Create uploads directory
mkdir -p /tmp/uploads/employees

# Use default port 5000 if $PORT is not set
PORT=${PORT:-5000}

# Start the application
exec gunicorn --bind 0.0.0.0:$PORT app:app