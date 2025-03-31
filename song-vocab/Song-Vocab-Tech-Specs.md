# Tech Specs

## Business Goals
We want to create a program that will find lyrics off the internetfor a taget song in a specific language and produce vocabulary to be imported into our database.

## Technical Requirements
- Python 3.12
- FastAPI
- Instructor for structured json output
- Ollama via Python SDK (for being the LLM)
    - Mistral 7B
- SQLite
- duckduckgo-search-python (to search for lyrics)

## API Endpoints

### Get Lyrics

POST /api/agent

### Behavior
- This endpoint goes to our agent which uses the reACT framework so that it can go to the web and finds mutiple possible versions of lycris and then extracts out the correctlyrics and then format the lyrics into vocabulary

Tools available to the agent:
- tools/search_web.py
- tools/get_page_content.py
- tools/extract_vocab.py

### Request Parameters
- message_request: str
    - This is the message request from the user that describes the song and/or artist they want to find lyrics for.

### Response
- lyrics: str
    - This is the lyrics of the song found in the web.
- vocab: list
    - This is the list of vocabulary words found in the lyrics in a specific json format.
