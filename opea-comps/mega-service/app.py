from fastapi import HTTPException
import json
import time
import os
from dataclasses import dataclass

from comps import MicroService, ServiceOrchestrator
from comps.cores.mega.constants import ServiceType, ServiceRoleType
from comps.cores.proto.api_protocol import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionResponseChoice,
    ChatMessage,
    UsageInfo,
)

EMBEDDING_SERVICE_HOST_IP = os.getenv("EMBEDDING_SERVICE_HOST_IP", "0.0.0.0")
EMBEDDING_SERVICE_PORT = os.getenv("EMBEDDING_SERVICE_PORT", 6000)
LLM_SERVICE_HOST_IP = os.getenv("LLM_SERVICE_HOST_IP", "0.0.0.0")
LLM_SERVICE_PORT = os.getenv("LLM_SERVICE_PORT", 8008)

@dataclass
class LLMParams:
    max_tokens: int = 1024
    temperature: float = 0.01
    stream: bool = True
    top_k: int = 10
    top_p: float = 0.95
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    repetition_penalty: float = 1.03
    chat_template: str = None

class ChatService:
    def __init__(self, host="0.0.0.0", port=8000):
        self.host = host
        self.port = port
        self.endpoint = "/v1/chat/completions"
        self.megaservice = ServiceOrchestrator()

    def add_remote_service(self):
        # embedding = MicroService(
        #     name="embedding",
        #     host=EMBEDDING_SERVICE_HOST_IP,
        #     port=EMBEDDING_SERVICE_PORT,
        #     endpoint="/v1/embeddings",
        #     use_remote_service=True,
        #     service_type=ServiceType.EMBEDDING,
        # )
        llm = MicroService(
            name="llm",
            host=LLM_SERVICE_HOST_IP,
            port=LLM_SERVICE_PORT,
            endpoint="/v1/chat/completions",
            use_remote_service=True,
            service_type=ServiceType.LLM,
        )
        self.megaservice.add(llm)
        # self.megaservice.flow_to(embedding, llm)

    async def handle_request(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        try:
            # Format the request for Ollama
            ollama_request = {
                "model": request.model or "llama3.2:1b",  # or whatever default model you're using
                "messages": [
                    {
                        "role": "user",
                        "content": request.messages  # assuming messages is a string
                    }
                ],
                "stream": False  # disable streaming for now
            }
            
            # Schedule the request through the orchestrator
            result = await self.megaservice.schedule(ollama_request)
            
            # Extract the actual content from the response
            if isinstance(result, tuple) and len(result) > 0:
                llm_response = result[0].get('llm/MicroService')
                if hasattr(llm_response, 'body'):
                    # Read and process the response
                    response_body = b""
                    async for chunk in llm_response.body_iterator:
                        response_body += chunk
                    content = response_body.decode('utf-8')
                else:
                    content = "No response content available"
            else:
                content = "Invalid response format"

            # Create the response
            response = ChatCompletionResponse(
                model=request.model or "example-model",
                choices=[
                    ChatCompletionResponseChoice(
                        index=0,
                        message=ChatMessage(
                            role="assistant",
                            content=content
                        ),
                        finish_reason="stop"
                    )
                ],
                usage=UsageInfo(
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0
                )
            )
            
            return response
            
        except Exception as e:
            # Handle any errors
            raise HTTPException(status_code=500, detail=str(e))

    def start(self):

        self.service = MicroService(
            self.__class__.__name__,
            service_role=ServiceRoleType.MEGASERVICE,
            host=self.host,
            port=self.port,
            endpoint=self.endpoint,
            input_datatype=ChatCompletionRequest,
            output_datatype=ChatCompletionResponse,
        )

        self.service.add_route(self.endpoint, self.handle_request, methods=["POST"])

        self.service.start()

example_service = ChatService()
example_service.add_remote_service()
example_service.start()
