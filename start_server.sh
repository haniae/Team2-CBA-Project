#!/bin/bash

# Start the BenchmarkOS Chatbot Server
# Sets up PYTHONPATH and starts the server

cd /home/malcolm-munoriyarwa/projects/Team2-CBA-Project

export PYTHONPATH=/home/malcolm-munoriyarwa/projects/Team2-CBA-Project/src:$PYTHONPATH

echo "Starting BenchmarkOS Chatbot Server..."
echo "PYTHONPATH: $PYTHONPATH"
echo ""

python3 -m benchmarkos_chatbot.web

