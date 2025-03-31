#!/bin/bash

curl -X POST http://localhost:8000/api/agent \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Find lyrics for Shape of You by Ed Sheeran"
  }' | jq