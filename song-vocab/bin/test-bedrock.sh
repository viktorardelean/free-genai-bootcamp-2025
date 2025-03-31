#!/bin/bash

# Test the Bedrock lyrics agent
curl -X POST http://localhost:8000/api/bedrock \
  -H "Content-Type: application/json" \
  -d '{"message": "Shape of You"}'

# Test with different songs
# curl -X POST http://localhost:8000/api/bedrock \
#   -H "Content-Type: application/json" \
#   -d '{"message": "Bohemian Rhapsody"}'

# curl -X POST http://localhost:8000/api/bedrock \
#   -H "Content-Type: application/json" \
#   -d '{"message": "Yesterday by Beatles"}' 