from fastapi import APIRouter
from typing import Optional
from app.schemas import IndexRequest
from app.services.indexer import start_indexing, get_job_status

router = APIRouter()

@router.post("/api/index/start")
async def start_index(req: Optional[IndexRequest] = None):
    """Start indexing a repository. Pass repo_url to index any GitHub repo."""
    repo_url = req.repo_url if req else None
    job_id = await start_indexing(repo_url=repo_url)
    return {"job_id": job_id}

@router.post("/api/index")
async def index_repo(req: Optional[IndexRequest] = None):
    """Start indexing with optional custom repo URL or path."""
    repo_url = req.repo_url if req else None
    path = req.path if req else None
    incremental = req.incremental if req else False
    job_id = await start_indexing(repo_url=repo_url, path=path, incremental=incremental)
    return {"job_id": job_id}

@router.get("/api/index/status/{job_id}")
async def index_status(job_id: str):
    return await get_job_status(job_id)
