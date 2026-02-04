"""
Memory Manager using mem0ai
Adapted from IntelligentAgent project.
"""

import os
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from config.config import QdrantConfig, OllamaConfig, get_config

try:
    from mem0 import Memory
except ImportError:
    Memory = None

logger = logging.getLogger("memory_manager")


class MemoryManager:
    """Manages agent memory using mem0."""

    def __init__(self, user_id: str = "default_user"):
        self.user_id = user_id
        self.memory = None

        # Load configuration
        self.config = get_config()
        self.qdrant_config = self.config.qdrant
        self.ollama_config = self.config.ollama

        provider = self.config.vector_db.provider

        if Memory:
            try:
                # Configure Vector Store based on provider
                vector_store_config = {}

                if provider == "qdrant":
                    vector_store_config = {
                        "provider": "qdrant",
                        "config": {
                            "host": self.qdrant_config.host,
                            "port": self.qdrant_config.port,
                            "collection_name": self.qdrant_config.collection,
                            "embedding_model_dims": 768,
                        },
                    }
                elif provider == "chroma":
                    db_path = (
                        Path(self.config.vector_db.chroma_persist_dir) / "mem0_chroma"
                    )
                    os.makedirs(db_path, exist_ok=True)
                    vector_store_config = {
                        "provider": "chroma",
                        "config": {
                            "collection_name": "yaver_memory",
                            "path": str(db_path),
                        },
                    }
                elif provider == "leann":
                    # Fallback to Chroma for Episodic Memory even if Leann is used for Code
                    # to keep dependencies simple for Mem0
                    logger.info(
                        "Using ChromaDB for Episodic Memory (LEANN selected for Code)"
                    )
                    db_path = (
                        Path(self.config.vector_db.chroma_persist_dir)
                        / "mem0_chroma_leann"
                    )
                    os.makedirs(db_path, exist_ok=True)
                    vector_store_config = {
                        "provider": "chroma",
                        "config": {
                            "collection_name": "yaver_memory_leann_backed",
                            "path": str(db_path),
                        },
                    }
                else:
                    # Default
                    vector_store_config = {
                        "provider": "qdrant",
                        "config": {
                            "host": self.qdrant_config.host,
                            "port": self.qdrant_config.port,
                            "collection_name": self.qdrant_config.collection,
                        },
                    }

                # Global Config
                mem0_config = {
                    "vector_store": vector_store_config,
                    "llm": {
                        "provider": "ollama",
                        "config": {
                            "model": self.ollama_config.model_general,
                            "temperature": 0.1,
                        },
                    },
                    "embedder": {
                        "provider": "ollama",
                        "config": {"model": self.ollama_config.model_embedding},
                    },
                }

                logger.info(
                    f"Initializing mem0 with provider={provider}, Ollama={self.ollama_config.model_general}"
                )
                self.memory = Memory.from_config(mem0_config)
                logger.info("mem0 initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize mem0: {e}")
        else:
            logger.warning("mem0ai package not installed")

    def add(self, text: str, user_id: str = None, metadata: Dict = None):
        """Add memory."""
        if self.memory:
            self.memory.add(
                text, user_id=user_id or self.user_id, metadata=metadata or {}
            )
        else:
            logger.warning("Memory not initialized, skipping add")

    def search(self, query: str, user_id: str = None, limit: int = 5) -> List[Dict]:
        """Search memory."""
        if self.memory:
            return self.memory.search(
                query, user_id=user_id or self.user_id, limit=limit
            )
        return []

    def get_all(self, user_id: str = None) -> List[Dict]:
        """Get all memories."""
        if self.memory:
            return self.memory.get_all(user_id=user_id or self.user_id)
        return []

    def delete(self, memory_id: str):
        """Delete a memory."""
        if self.memory:
            self.memory.delete(memory_id)

    def delete_all(self, user_id: str = None):
        """Delete all memories for user."""
        if self.memory:
            self.memory.delete_all(user_id=user_id or self.user_id)
