# apps/indexer-agent/app/indexing/repository_manager.py
import asyncio
import hashlib
import shutil
from functools import partial
from git import Repo, InvalidGitRepositoryError
from pathlib import Path
from ..config import settings
from ..indexing.file_indexer import index_file


def _repo_dir_for_url(repo_url: str) -> str:
    """Derive a unique repo directory from the URL."""
    slug = repo_url.rstrip("/").rstrip(".git").split("/")[-1]
    url_hash = hashlib.md5(repo_url.encode()).hexdigest()[:8]
    return str(Path(settings.REPO_DIR) / f"{slug}-{url_hash}")


def _update_repo_sync(repo_url: str, repo_dir: str):
    """Synchronous git operations (run in executor)."""
    repo_path = Path(repo_dir)
    git_dir = repo_path / ".git"

    if git_dir.exists():
        try:
            Repo(repo_dir).remotes.origin.pull()
        except Exception:
            shutil.rmtree(repo_path, ignore_errors=True)
            Repo.clone_from(repo_url, repo_dir)
    else:
        if repo_path.exists():
            shutil.rmtree(repo_path, ignore_errors=True)
        Repo.clone_from(repo_url, repo_dir)


async def update_repo(repo_url: str, repo_dir: str):
    """Run git operations in thread pool to avoid blocking."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _update_repo_sync, repo_url, repo_dir)


async def index_repository(repo_url: str | None = None):
    """Clone/pull a repository and index all Python files."""
    url = repo_url or settings.REPO_URL
    if not url:
        return {"error": "No repository URL provided. Pass a repo_url parameter or set REPO_URL env var."}

    repo_dir = _repo_dir_for_url(url)
    await update_repo(url, repo_dir)

    py_files = list(Path(repo_dir).rglob("*.py"))

    indexed = 0
    batch_size = 3

    for i in range(0, len(py_files), batch_size):
        batch = py_files[i:i + batch_size]
        try:
            await asyncio.gather(*[index_file(str(f)) for f in batch])
            indexed += len(batch)
        except Exception as e:
            print(f"Batch indexing error: {e}")
            for f in batch:
                try:
                    await index_file(str(f))
                    indexed += 1
                except Exception:
                    pass

    return {"indexed_files": indexed, "repo_url": url, "repo_dir": repo_dir}
