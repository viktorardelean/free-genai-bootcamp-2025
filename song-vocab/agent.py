from typing import List, Dict
from pydantic import BaseModel
from ollama import AsyncClient
from tools.search_web import search_web
from tools.get_page_content import get_page_content
from tools.extract_vocab import extract_vocab
import pathlib
import os
import logging
import json

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class AgentResponse(BaseModel):
    thought: str
    tool_name: str  # Required
    tool_args: Dict  # Required
    lyrics: str | None = None
    vocab: List | None = None
    is_done: bool

class SongVocabAgent:
    def __init__(self):
        # Get environment variables with fallbacks
        host_ip = os.getenv('host_ip', '127.0.0.1')
        port = os.getenv('LLM_ENDPOINT_PORT', '8008')
        model = os.getenv('LLM_MODEL_ID', 'deepseek-r1:8b')
        
        # Configure Ollama client
        ollama_host = f"http://{host_ip}:{port}"
        logger.debug(f"Initializing Ollama client with host: {ollama_host}")
        
        try:
            self.client = AsyncClient(host=ollama_host)
            self.model = model
            logger.debug(f"Ollama client initialized successfully with model: {model}")
        except Exception as e:
            logger.error(f"Failed to initialize Ollama client: {e}")
            raise
        
        # Initialize steps first
        self.current_step = 0
        self.steps = ["search", "get_content", "extract_vocab", "complete"]
        
        # Then initialize tools
        self.tools = {
            "search_web": search_web,
            "get_page_content": get_page_content,
            "extract_vocab": extract_vocab
        }
        
        # Then initialize step instructions
        self.step_instructions = {
            "search": {
                "tool": "search_web",
                "next": "get_content",
                "instruction": "Search for lyrics URL"
            },
            "get_content": {
                "tool": "get_page_content",
                "next": "extract_vocab",
                "instruction": "Get raw content from URL"
            },
            "extract_vocab": {
                "tool": "extract_vocab",
                "next": "complete",
                "instruction": "Extract vocabulary from lyrics"
            },
            "complete": {
                "tool": None,
                "next": None,
                "instruction": "Return final results"
            }
        }
        
        # Load prompt from file
        prompt_path = pathlib.Path(__file__).parent / "prompts" / "Lyrics-Agent.md"
        with open(prompt_path, 'r') as f:
            self.system_prompt = f.read()
        
        # Finally set up format reminder
        self.format_reminder = f"""
CRITICAL - FOLLOW EXACT WORKFLOW:
1. Current step: {self.steps[self.current_step]}
2. Required tool: {self.step_instructions[self.steps[self.current_step]]['tool']}
3. Next step: {self.step_instructions[self.steps[self.current_step]]['next']}

YOU MUST USE THIS FORMAT:
{{
    "thought": "your thought",
    "tool_name": "{self.step_instructions[self.steps[self.current_step]]['tool']}",
    "tool_args": {{"required": "arguments"}},
    "lyrics": "",
    "vocab": [],
    "is_done": false
}}
"""
        self.system_prompt = self.format_reminder + "\n" + self.system_prompt
        
    async def run(self, user_message: str) -> Dict:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "system", "content": f"""
STRICT WORKFLOW ENFORCEMENT:
1. You are on step: {self.steps[self.current_step]}
2. You MUST use tool: {self.step_instructions[self.steps[self.current_step]]['tool']}
3. After this step you MUST move to: {self.step_instructions[self.steps[self.current_step]]['next']}
4. DO NOT repeat steps
5. DO NOT skip steps

Example response for current step:
{{
    "thought": "your thought",
    "tool_name": "{self.step_instructions[self.steps[self.current_step]]['tool']}",
    "tool_args": {{"query": "example"}} if searching else {{"url": "example"}} if getting content else {{"text": "example"}},
    "lyrics": "",
    "vocab": [],
    "is_done": false
}}
"""},
            {"role": "user", "content": user_message}
        ]
        
        while True:
            try:
                response = await self.get_next_step(messages)
                logger.debug(f"Got response from Ollama: {response}")
                
                if response.is_done:
                    return {
                        "lyrics": response.lyrics,
                        "vocab": response.vocab
                    }
                
                # Execute tool and track step
                tool_result = await self.execute_tool(response.tool_name, response.tool_args)
                
                # Force step progression
                if response.tool_name != self.step_instructions[self.steps[self.current_step]]['tool']:
                    raise ValueError(f"Wrong tool used. Expected {self.step_instructions[self.steps[self.current_step]]['tool']}, got {response.tool_name}")
                
                self.current_step = min(self.current_step + 1, len(self.steps) - 1)
                next_step = self.steps[min(self.current_step + 1, len(self.steps)-1)]
                
                messages.append({"role": "assistant", "content": response.thought})
                messages.append({
                    "role": "system", 
                    "content": f"""
CURRENT STEP: {self.steps[self.current_step]}
INSTRUCTION: {self.step_instructions[self.steps[self.current_step]]['instruction']}
NEXT STEP: {next_step}

REMEMBER:
1. Use exact JSON format
2. Do not modify or structure the content
3. Move immediately to next step
4. Keep raw lyrics as-is
"""
                })
                messages.append({"role": "system", "content": f"Tool result: {tool_result}"})
            except Exception as e:
                logger.error(f"Error during agent run: {e}")
                raise
        
    async def get_next_step(self, messages: List[Dict]) -> AgentResponse:
        try:
            # Add format enforcement to every message exchange
            messages = [
                {"role": "system", "content": "You must respond with valid JSON only."},
                {"role": "system", "content": self.format_reminder},
                *messages
            ]
            
            response = await self.client.chat(
                model=self.model,
                messages=messages,
                format="json"
            )
            logger.debug(f"Raw Ollama response: {response}")
            
            try:
                json_response = response.model_dump()["message"]["content"]
                logger.debug(f"Parsed JSON response: {json_response}")
                return AgentResponse.parse_raw(json_response)
            except Exception as e:
                logger.error(f"Failed to parse response: {e}", exc_info=True)
                logger.error(f"Raw response was: {response}")
                raise
        except Exception as e:
            logger.error(f"Ollama API call failed: {e}", exc_info=True)
            raise
        
    async def execute_tool(self, tool_name: str, tool_args: Dict) -> str:
        logger.debug(f"Executing tool: {tool_name} with args: {tool_args}")
        tool = self.tools.get(tool_name)
        if not tool:
            raise Exception(f"Unknown tool: {tool_name}")
        try:
            result = await tool(**tool_args)
            logger.debug(f"Tool execution successful: {type(result)}")
            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {str(e)}", exc_info=True)
            raise 