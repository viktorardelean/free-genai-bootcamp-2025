# Mega Service

A FastAPI-based service that orchestrates communication between an embedding service and an LLM service.

## Overview

This service acts as an orchestrator that:
- Handles chat completion requests
- Coordinates between embedding and LLM services
- Exposes a REST API endpoint for chat completions

## Environment Variables

The service uses the following environment variables:

- `EMBEDDING_SERVICE_URL`: URL of the embedding service
- `LLM_SERVICE_URL`: URL of the LLM service
- `PORT`: Port on which the service will run

## Usage

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set environment variables:
   ```bash
   export EMBEDDING_SERVICE_URL=http://localhost:8000
   export LLM_SERVICE_URL=http://localhost:9000
   export PORT=8000
   ```

3. Start the service:
   ```bash
   python app.py
   ```

## API Endpoints

The service exposes the following API endpoints:

- `POST /v1/chat/completions`: Handles chat completion requests

## Example Usage


```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "llama3.2:1b", "messages": [{"role": "user", "content": "Hello, how are you?"}]}'
```

