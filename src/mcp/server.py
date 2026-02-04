"""
Yaver MCP Server
Exposes Yaver's coding and memory capabilities via Model Context Protocol.
"""

import logging
from typing import List
from mcp.server.fastmcp import FastMCP, Context

# Initialize FastMCP
mcp = FastMCP("Yaver")

# Lazy initialization of services to avoid startup overhead if not used
_services = {}


def get_services():
    """Lazy load services."""
    if _services:
        return _services

    try:
        from config.config import get_config
        from tools.rag.rag_service import RAGService
        from memory.manager import MemoryManager
        from tools.code_analyzer.vector_store import VectorStoreFactory
        from tools.code_analyzer.embeddings import CodeEmbedder
        from tools.code_analyzer.neo4j_adapter import Neo4jAdapter

        config = get_config()

        vector_store = VectorStoreFactory.get_instance(config.vector_db)
        embedder = CodeEmbedder(config.ollama)
        neo4j = Neo4jAdapter(
            config.neo4j.uri, (config.neo4j.username, config.neo4j.password)
        )

        rag = RAGService(neo4j, vector_store, embedder, config.ollama)
        memory = MemoryManager()

        _services["rag"] = rag
        _services["memory"] = memory

    except Exception as e:
        logging.error(f"Failed to initialize Yaver services: {e}")
        raise

    return _services


@mcp.tool()
async def ask_yaver(question: str) -> str:
    """
    Ask Yaver a question about the codebase or general programming topics.
    Uses RAG (Neo4j + Vector DB) to answer.
    """
    services = get_services()
    rag = services["rag"]

    # Use RAG to answer
    answer = rag.answer(question)
    return answer


@mcp.tool()
async def search_code(query: str) -> str:
    """
    Search the codebase for snippets matching the query.
    Returns raw code snippets.
    """
    services = get_services()
    rag = services["rag"]

    # Retrieve context only
    context = rag.retrieve_context(query, strategy="HYBRID")
    return context


@mcp.resource("yaver://memory/recent")
async def get_recent_memory() -> str:
    """
    Get the most recent conversation memories.
    """
    services = get_services()
    memory = services["memory"]

    memories = memory.get_all_memories()
    # Format as string
    text = "Recent Memories:\n"
    for m in memories[-10:]:
        text += f"- {m.get('memory', m)}\n"

    return text


if __name__ == "__main__":
    mcp.run()
