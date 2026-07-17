from fastapi import APIRouter, HTTPException

from app.models.chat import ChatRequest, ChatResponse
from app.services.cache import CacheService
from app.services.llm import LLMService
from app.services.prompt import build_system_prompt

router = APIRouter()
cache_service = CacheService()
llm_service = LLMService()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    history = [message.model_dump() for message in request.history]
    cached_reply = cache_service.get(question=request.message)
    if cached_reply:
        return ChatResponse(reply=cached_reply, cached=True)

    system_prompt = build_system_prompt()

    reply = llm_service.generate_reply(request.message, history=history, system_prompt=system_prompt)
    if not reply:
        raise HTTPException(status_code=500, detail="Failed to generate reply")

    cache_service.set(value=reply, question=request.message, response=reply)
    return ChatResponse(reply=reply, cached=False)
