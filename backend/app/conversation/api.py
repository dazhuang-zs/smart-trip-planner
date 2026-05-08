"""对话 API 路由"""
from fastapi import APIRouter
from app.conversation.agent import TripAgent
from app.conversation.message import ChatRequest, ChatResponse
from app.conversation.store import store

router = APIRouter(prefix="/api/v1/conversation", tags=["对话"])


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """
    多轮对话接口

    用户可以：
    - 首次对话：不传conversation_id，自动创建新对话
    - 继续对话：传入conversation_id，Agent会读取历史状态
    """
    agent = TripAgent()
    result = await agent.chat(
        message=req.message,
        conversation_id=req.conversation_id,
    )
    return ChatResponse(**result)


@router.get("/history/{conversation_id}")
async def get_history(conversation_id: str) -> dict:
    """获取对话历史"""
    messages = store.get_messages(conversation_id)
    state = store.get_state(conversation_id)
    return {
        "conversation_id": conversation_id,
        "messages": messages,
        "state": state,
    }


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str) -> dict:
    """删除对话"""
    store.delete(conversation_id)
    return {"success": True, "message": "对话已删除"}
