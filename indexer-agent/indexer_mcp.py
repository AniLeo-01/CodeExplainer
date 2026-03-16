import ast
import os
from typing import Optional
from fastmcp import FastMCP
from app.indexing.repo_manager import index_repository
from app.indexing.file_indexer import index_file
from app.indexing.ast_parser import parse_python_ast
from app.indexing.entity_extractor import extract_entities

mcp = FastMCP(name="Indexer Agent")

@mcp.tool
async def index_repo(repo_url: Optional[str] = None) -> dict:
    """Index a GitHub repository. Pass a repo_url or uses the configured default."""
    return await index_repository(repo_url)

@mcp.tool
async def index_single_file(path: str) -> dict:
    """Index a given Python file."""
    return await index_file(path)

@mcp.tool
async def parse_ast(path: str) -> dict:
    """Return AST node count for the file."""
    tree = await parse_python_ast(path)
    return {"nodes": len(list(ast.walk(tree)))}

@mcp.tool
async def extract_code_entities(path: str) -> dict:
    """Extract entities and push to Neo4j."""
    tree = await parse_python_ast(path)
    await extract_entities(tree, path)
    return {"status": "ok", "file": path}

@mcp.tool
async def index_status() -> dict:
    """Indexer health/status."""
    return {"ready": True, "service": "indexer-agent"}

if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "http":
        port = int(os.environ.get("MCP_PORT", "8003"))
        mcp.run(transport="http", host="0.0.0.0", port=port)
    else:
        mcp.run()  # Default stdio for subprocess mode
