#!/bin/bash

# Activate the virtual environment if it exists
if [ -d "../../../.venv" ]; then
    source ../../../.venv/bin/activate
elif [ -d "../.venv" ]; then
    source ../.venv/bin/activate
fi

# Install dependencies if needed
pip install -r requirements.txt

# Run the Flask application (runs on port 5001)
python app.py 