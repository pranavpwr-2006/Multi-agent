import os
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from personal_assistant.agent import root_agent

app = FastAPI(title="Sora Assistant")

session_service = InMemorySessionService()
runner = Runner(
    agent=root_agent,
    app_name="sora_assistant",
    session_service=session_service,
)

class MessageRequest(BaseModel):
    session_id: str
    message: str

@app.get("/")
def health_check():
    return {"status": "ok", "agent": "sora_assistant"}

@app.post("/chat")
async def chat(request: MessageRequest):
    session = await session_service.get_session(
        app_name="sora_assistant",
        user_id="user",
        session_id=request.session_id,
    )
    if not session:
        session = await session_service.create_session(
            app_name="sora_assistant",
            user_id="user",
            session_id=request.session_id,
        )

    content = Content(parts=[Part(text=request.message)])
    response_text = ""

    async for event in runner.run_async(
        user_id="user",
        session_id=request.session_id,
        new_message=content,
    ):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if part.text:
                    response_text += part.text

    return {"response": response_text}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)