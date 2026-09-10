#!/usr/bin/env python3
"""Serve the Lesson 01 TravelAgent over HTTP so it can be smoke-tested.

Run from this directory:
    python 01-serve-travel-agent.py                     # listens on http://127.0.0.1:8000
In a second terminal, from the repository root:
    python tests/run_smoke_tests.py tests/lesson-01-smoke-tests.json --url http://localhost:8000

Routes (contract in tests/README.md):
    GET  /health -> {"status": "ok", "version": "lesson-01"}
    POST /chat   {"message": str, "conversation_id": str | null} -> {"reply": str, "conversation_id": str}
"""
import json
import os
import uuid

from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel

load_dotenv(find_dotenv())
llm = ChatOpenAI(
    model=os.environ["LLM_MODEL"],
    base_url=os.environ["LLM_BASE_URL"],
    api_key=os.environ["LLM_API_KEY"],
    extra_body=json.loads(os.environ.get("LLM_EXTRA_BODY") or "null"),
)

# --- the lesson's tools and system prompt, identical to the notebook ---------
# (the prompt adds one scope sentence so off-topic requests are declined)


@tool
def get_destinations() -> list[str]:
    """Get a list of popular vacation destinations."""
    return [
        "Barcelona", "Paris", "Berlin", "Tokyo", "Sydney",
        "New York City", "Cairo", "Cape Town", "Rio de Janeiro", "Bali",
    ]


SYSTEM_PROMPT = (
    "You are a helpful travel agent. Help users find their perfect vacation "
    "destination based on their preferences. Use the get_destinations tool "
    "to see available destinations. Only help with travel planning; politely "
    "decline any other request and never write code."
)

agent = create_agent(llm, tools=[get_destinations], system_prompt=SYSTEM_PROMPT, checkpointer=InMemorySaver())
app = FastAPI(title="Lesson 01 TravelAgent")


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    conversation_id: str


def reply_text(result) -> str:
    content = result["messages"][-1].content
    if isinstance(content, list):
        return "".join(block.get("text", "") for block in content if isinstance(block, dict))
    return content


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": "lesson-01"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    thread_id = request.conversation_id or str(uuid.uuid4())
    result = agent.invoke(
        {"messages": [{"role": "user", "content": request.message}]},
        {"configurable": {"thread_id": thread_id}},
    )
    return ChatResponse(reply=reply_text(result), conversation_id=thread_id)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "8000")))
