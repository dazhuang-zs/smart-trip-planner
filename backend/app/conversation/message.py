"""消息模型"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal


class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ToolCall(BaseModel):
    name: str
    arguments: dict


class ToolResult(BaseModel):
    name: str
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="用户消息")
    conversation_id: Optional[str] = Field(None, description="对话ID，空则创建新对话")
    conversation_history: Optional[List[Message]] = Field(default_factory=list, description="历史消息")


class ChatResponse(BaseModel):
    conversation_id: str
    message: str
    tool_calls: List[ToolResult] = Field(default_factory=list)
    state: str
    data: Optional[dict] = None
    suggestions: List[str] = Field(default_factory=list)
