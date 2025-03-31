#!/bin/bash

# Source environment variables
source ../../opea-comps/ollama-variables.env

# Enable debug output
export PYTHONPATH=.
export PYTHONDEVMODE=1

# Test the lyrics agent
curl -X POST http://localhost:8000/api/agent \
  -H "Content-Type: application/json" \
  -d '{"song": "Shape of You"}'

# Run with detailed logging
curl -v -X POST http://localhost:8000/api/agent \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Find lyrics for Shape of You by Ed Sheeran"
  }' | jq 