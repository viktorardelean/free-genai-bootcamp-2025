from comps import ServiceOrchestrator, ServiceRoleType, MicroService
from comps.cores.proto.api_protocol import (
    ChatCompletionRequest,
    ChatCompletionResponse,
)
from fastapi import Request

class Chat:
    def __init__(self):
        print("Chat initialized")
        self.megaservice = ServiceOrchestrator()
        self.endpoint = "/chat"
        self.host = "0.0.0.0"
        self.port = 8888
    def add_remote_service(self):
        print("Adding remote service")
    def start(self):
        print("Starting chat")
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

    def handle_request(self, request: Request):
        print("Handling request")
       

if __name__ == "__main__":
    chat = Chat()
    chat.add_remote_service()
    chat.start()