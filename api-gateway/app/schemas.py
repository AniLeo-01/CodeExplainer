from pydantic import BaseModel
from typing import Optional, Any

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    stream: bool = False

class ChatResponse(BaseModel):
    session_id: str
    response: Any

class IndexRequest(BaseModel):
    repo_url: Optional[str] = None
    path: Optional[str] = None
    incremental: bool = False
