# Song Vocab

A service that finds song lyrics and extracts vocabulary to help language learners.

## Prerequisites

- Python 3.12
- Ollama running in Docker (using opea-comps setup)
- `jq` command-line tool (optional, for pretty-printing JSON)

## Setup

1. Clone the repository and navigate to the project:
```bash
cd song-vocab
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the App

1. Make sure your Ollama container is running:
```bash
cd ../opea-comps
docker compose up -d

# Pull the Mistral model (first time only)
docker exec -it ollama ollama pull mistral

# Verify Ollama is working:
# List available models
docker exec -it ollama ollama list

# Test the model
docker exec -it ollama ollama run mistral:7b "Hello, how are you?"

# Test the API endpoint
curl http://127.0.0.1:8008/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral:7b",
    "messages": [
      {
        "role": "user",
        "content": "Hello, how are you?"
      }
    ]
  }'
```

2. Source the Ollama environment variables and start the app:
```bash
cd ../song-vocab  # Go back to song-vocab directory
source ../opea-comps/ollama-variables.env
uvicorn app:app --reload
```

## Testing

Use the provided test script:
```bash
chmod +x bin/test.sh  # Make script executable (first time only)
./bin/test.sh
```

[Rest of README...]