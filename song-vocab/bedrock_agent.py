import boto3
import json
import logging
from typing import Dict, List
from pydantic import BaseModel
import pathlib
import os
from tools.search_web import search_web
from tools.get_page_content import get_page_content
from tools.extract_vocab import extract_vocab
import html

logger = logging.getLogger(__name__)

class AgentResponse(BaseModel):
    thought: str
    tool_name: str
    tool_args: Dict
    lyrics: str | None = None
    vocab: List | None = None
    is_done: bool

class BedrockSongAgent:
    def __init__(self):
        # Initialize AWS Bedrock client
        self.bedrock = boto3.client(
            service_name='bedrock-runtime',
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        
        # Initialize steps and tools
        self.current_step = 0
        self.steps = ["search", "get_content", "extract_vocab", "complete"]
        
        self.tools = {
            "search_web": search_web,
            "get_page_content": get_page_content,
            "extract_vocab": extract_vocab
        }
        
        # Load and prepare prompt
        prompt_path = pathlib.Path(__file__).parent / "prompts" / "Lyrics-Agent.md"
        with open(prompt_path, 'r') as f:
            self.system_prompt = f.read()
            
    async def invoke_model(self, messages: List[Dict]) -> Dict:
        try:
            body = {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": self.format_messages(messages)}]
                    }
                ]
            }
            
            response = self.bedrock.invoke_model(
                modelId='amazon.nova-micro-v1:0',
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body)
            )
            
            response_body = json.loads(response.get('body').read())
            logger.debug(f"Raw response from Bedrock: {response_body}")
            
            # Extract the text content from Nova's response structure
            text_content = response_body['output']['message']['content'][0]['text']
            
            # Remove markdown code block markers if present
            text_content = text_content.replace('```json\n', '').replace('\n```', '')
            
            # Parse JSON directly - no fallbacks
            parsed = json.loads(text_content)
            return json.dumps(parsed)
            
        except Exception as e:
            logger.error(f"Bedrock API call failed: {e}")
            raise
            
    def format_messages(self, messages: List[Dict]) -> str:
        """Format messages for Nova model input"""
        formatted = []
        for msg in messages:
            if msg["role"] == "system":
                formatted.append(f"System: {msg['content']}")
            elif msg["role"] == "user":
                formatted.append(f"Human: {msg['content']}")
            elif msg["role"] == "assistant":
                formatted.append(f"Assistant: {msg['content']}")
        return "\n".join(formatted)
            
    async def run(self, user_message: str) -> Dict:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        while True:
            try:
                response_text = await self.invoke_model(messages)
                response = AgentResponse.parse_raw(response_text)
                logger.debug(f"Got response from Bedrock: {response}")
                
                if response.is_done:
                    # Transform vocab list into english/spanish pairs
                    vocab_pairs = []
                    seen_words = set()
                    
                    for item in response.vocab:
                        word = item["word"].lower().strip()
                        if word not in seen_words and len(word) > 2:  # Skip short words
                            seen_words.add(word)
                            vocab_pairs.append({
                                "english": word,
                                "spanish": ""  # You'll need to integrate with a translation service
                            })
                    
                    return {
                        "lyrics": response.lyrics,
                        "vocab": vocab_pairs
                    }
                
                # Execute tool
                tool_result = await self.execute_tool(response.tool_name, response.tool_args)
                
                # Add the full response and tool result to conversation
                messages.append({
                    "role": "assistant", 
                    "content": response_text
                })
                
                # Properly serialize the tool result
                if isinstance(tool_result, str):
                    tool_result_str = tool_result
                else:
                    tool_result_str = json.dumps(tool_result)
                
                messages.append({
                    "role": "system", 
                    "content": f"Tool result: {tool_result_str}"
                })
                
            except Exception as e:
                logger.error(f"Error during agent run: {e}")
                raise
                
    async def execute_tool(self, tool_name: str, tool_args: Dict) -> str:
        logger.debug(f"Executing tool: {tool_name} with args: {tool_args}")
        tool = self.tools.get(tool_name)
        if not tool:
            raise Exception(f"Unknown tool: {tool_name}")
        try:
            result = await tool(**tool_args)
            logger.debug(f"Tool execution successful: {type(result)}")
            
            # Sanitize the result if it's a string
            if isinstance(result, str):
                # Decode HTML entities
                result = html.unescape(result)
                # Remove problematic characters and normalize
                result = ''.join(char for char in result if ord(char) < 128)
                # Clean up whitespace
                result = ' '.join(result.split())
            
            # Ensure result can be properly JSON serialized
            try:
                json.dumps({"result": result})  # Test JSON serialization
            except Exception as e:
                logger.warning(f"Failed to serialize result: {e}")
                if isinstance(result, str):
                    # Further sanitize if needed
                    result = result.replace('"', "'")
                    result = result.replace('\\', '/')
            
            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {str(e)}")
            raise 