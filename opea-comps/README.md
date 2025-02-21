# Ollama Server Setup

This guide explains how to run the Ollama server using Docker Compose.

## Prerequisites

- Docker and Docker Compose installed
- Basic understanding of environment variables

## Environment Variables

Before running the container, you need to set the following environment variables:

- `LLM_ENDPOINT_PORT`: Port to expose the Ollama server (defaults to 8008 if not set)
- `LLM_MODEL_ID`: The ID of the LLM model to use (https://ollama.com/library)
- `host_ip`: Your host machine's IP address
- `http_proxy`: HTTP proxy if required (optional)
- `https_proxy`: HTTPS proxy if required (optional)
- `no_proxy`: Addresses to exclude from proxy (optional)

## Running the Container

1. Create a `.env` file in the same directory as your docker-compose.yaml with your environment variables:
ollama-variables.env

LLM_ENDPOINT_PORT=8008
LLM_MODEL_ID=llama3.2:1b
host_ip=127.0.0.1

2. Start the container using Docker Compose:

```bash
docker compose --env-file ollama-variables.env up -d
```

3. To stop the container:

```bash
docker compose down
```

## Verifying the Installation

Once the container is running, you can verify it's working by:

```bash
curl http://localhost:8008
```

## Troubleshooting

If you encounter any issues:

1. Check if the container is running:
```bash
docker container ls | grep ollama-server
```

2. View container logs:
```bash
docker logs ollama-server
```

## Pull a model
The docker container does not contain any models. You can pull any ollama model using the following command.

```bash
curl http://localhost:8008/api/pull -d '{
  "model": "llama3.2:1b"
}'
```

## Running a prompt against the LLM

```bash
curl http://localhost:8008/api/generate -d '{
  "model": "llama3.2:1b",
  "prompt": "Why is the sky blue?"
}'
```

