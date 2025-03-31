#! /bin/bash

curl -X POST http://localhost:8888/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2:1b",
    "messages": [
      {
        "role": "user",
        "content": "Hello, world!"
      }
    ],
    "temperature": 0.5
  }'
