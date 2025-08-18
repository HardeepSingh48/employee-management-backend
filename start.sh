#!/bin/bash

# Create uploads directory
mkdir -p /tmp/uploads/employees

# Start the application
exec gunicorn --bind 0.0.0.0:$PORT app:app
