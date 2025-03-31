from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ValidationError
from agent import SongVocabAgent
from bedrock_agent import BedrockSongAgent
import logging

app = FastAPI(title="Song Vocab API")
logger = logging.getLogger(__name__)

class MessageRequest(BaseModel):
    message: str

class VocabResponse(BaseModel):
    lyrics: str
    vocab: list

class SongRequest(BaseModel):
    song: str

@app.post("/api/agent", response_model=VocabResponse)
async def process_song_request(request: MessageRequest):
    try:
        agent = SongVocabAgent()
        result = await agent.run(request.message)
        return VocabResponse(
            lyrics=result["lyrics"],
            vocab=result["vocab"]
        )
    except ValidationError as e:
        logger.error(f"Response format validation failed: {e}")
        raise HTTPException(status_code=500, detail="Agent response format invalid")
    except Exception as e:
        logger.error(f"Agent error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/bedrock", response_model=VocabResponse)
async def process_song_bedrock(request: MessageRequest):
    """Use Bedrock Claude 3 Sonnet for lyrics processing"""
    try:
        agent = BedrockSongAgent()
        result = await agent.run(request.message)
        return result
    except ValidationError as e:
        logger.error(f"Response format validation failed: {e}")
        raise HTTPException(status_code=500, detail="Agent response format invalid")
    except Exception as e:
        logger.error(f"Agent error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/agent")
async def process_song(request: SongRequest):
    try:
        agent = SongVocabAgent()
        result = await agent.run(request.song)
        return result
    except ValidationError as e:
        logger.error(f"Response format validation failed: {e}")
        raise HTTPException(status_code=500, detail="Agent response format invalid")
    except Exception as e:
        logger.error(f"Agent error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 