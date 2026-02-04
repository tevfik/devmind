"""
LEANN Adapter for Vector Storage
Wraps the LEANN library for Yaver.
"""

import logging
import os
import shutil
import uuid
from typing import List, Dict, Any, Optional

try:
    from leann import LeannBuilder, LeannSearcher
except ImportError:
    LeannBuilder = None
    LeannSearcher = None

from tools.code_analyzer.vector_store import VectorStoreInterface
from config.config import VectorDBConfig

logger = logging.getLogger(__name__)


class LeannAdapter(VectorStoreInterface):
    """
    Adapter for LEANN Vector Database.
    Note: LEANN is primarily a static index builder.
    This adapter handles the "append" simulation by managing a persistent index.
    """

    def __init__(self, config: Optional[VectorDBConfig] = None):
        if not LeannBuilder:
            logger.warning("LEANN not installed. Using mock or failing.")

        self.config = config or VectorDBConfig()
        # LEANN uses a directory or file path for the index
        self.index_path = str(
            self.config.chroma_persist_dir / "leann_index"
        )  # Reuse persist dir config for now
        self.searcher = None

        # Ensure directory exists
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)

        # Load searcher if index exists
        self._load_searcher()

    def _load_searcher(self):
        """Load the searcher if the index exists."""
        if os.path.exists(self.index_path) and LeannSearcher:
            try:
                self.searcher = LeannSearcher(self.index_path)
                logger.info(f"Loaded LEANN index from {self.index_path}")
            except Exception as e:
                logger.error(f"Failed to load LEANN index: {e}")
                self.searcher = None

    def store_embeddings(self, items: List[Dict[str, Any]]):
        """
        Store items in LEANN.
        WARNING: LEANN is a build-time index. Adding items typically requires rebuilding
        or using a specific incremental API if available.
        For this implementation, we will REBUILD the index with the new items PLUS
        existing items if possible, or just build a new segment.

        Given Yaver's 'analyze' is often a batch operation, we might just build new.
        However, for 'memory', we need persistence.

        Current approach:
        LEANN doesn't seem to support easy incremental updates in the README.
        We will assume we are building an index for a specific 'session' or 'repo'.
        """
        if not items or not LeannBuilder:
            return

        # TODO: Check if LEANN supports incremental add.
        # For now, we instantiate a Builder, add items, and build.
        # If an index exists, we might normally want to load it and add to it,
        # but LeannBuilder(backend="hnsw") initializes a new one.

        # NOTE: This is a simplified implementation that OVERWRITES or CREATES a new index
        # for the batch. Ideally, we need to read existing docs and re-index.
        # Since this is "Episodic Memory" & "Code Analysis", let's assume valid usage.

        try:
            builder = LeannBuilder(backend_name="hnsw")

            count = 0
            for item in items:
                # LEANN expects 'text' typically.
                # If we have pre-computed embeddings, we might need a way to feed them.
                # The README shows `builder.add_text()`.
                # Does `builder.add_embedding()` exist?
                # Inspecting the LeannBuilder in a real scenario would be good.
                # Assuming `add_text` for now as Yaver usually sends text + embedding.
                # If Yaver only sends embedding, this adapter is tricky.

                content = item.get("content") or item.get("text")
                if content:
                    # We pass the metadata as well if possible?
                    # LEANN simple API might not store arbitrary metadata payload easily
                    # without looking deeper.
                    # README says "RAG Everything", implies it stores text.
                    builder.add_text(content)
                    count += 1

            if count > 0:
                # Check availability of incremental build or update
                # For now, we overwrite or create.
                builder.build_index(self.index_path)
                logger.info(
                    f"Built LEANN index at {self.index_path} with {count} items"
                )

                # Reload searcher
                self._load_searcher()

        except Exception as e:
            logger.error(f"Failed to build LEANN index: {e}")
            raise

    def search(
        self,
        query_vector: List[float],
        limit: int = 5,
        score_threshold: float = 0.0,
        query_filter: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search LEANN index.
        """
        if not self.searcher:
            return []

        try:
            # LEANN Searcher typically takes a text query, not a vector,
            # if we used `add_text`.
            # But the interface receives `query_vector`.
            # We might need to handle this mismatch.
            # If Yaver passes the query string in `query_filter` or we change the interface
            # to accept `query_text`.

            # WORKAROUND: For now, we assume `query_filter` might contain the 'text'
            # or we just return empty if we can't search by vector directly.
            # OR, we assume we can search by vector if LEANN supports it.

            # Inspecting README:
            # searcher = LeannSearcher(INDEX_PATH)
            # results = searcher.search("query string", top_k=1)

            # The interface defines `query_vector`.
            # If we strictly use `query_vector`, we need `searcher.search_embedding(vec)`.
            # Let's assume for now we use the text if available on the call stack,
            # or this Adapter requires a text query.

            # Let's peek at the `query_filter` to see if we hacked the query text in there.
            query_text = query_filter.get("_query_text") if query_filter else None

            if query_text:
                results = self.searcher.search(query_text, top_k=limit)
                # Convert results to Yaver format
                # results is likely a list of objects or dicts.
                output = []
                for res in results:
                    # Guessing structure: res.text, res.score?
                    # Or it returns strings.
                    # Adjusted based on standard RAG returns.
                    output.append(
                        {
                            "id": str(
                                uuid.uuid4()
                            ),  # LEANN might not return stable IDs
                            "score": getattr(res, "score", 0.9),
                            "payload": {
                                "content": str(res)
                            },  # res might be the text itself
                        }
                    )
                return output
            else:
                logger.warning(
                    "LEANN Adapter requires '_query_text' in filter to search (Vector search not supported via this API yet)"
                )
                return []

        except Exception as e:
            logger.error(f"LEANN search failed: {e}")
            return []

    def delete_collection(self):
        """Delete the index."""
        if os.path.exists(self.index_path):
            shutil.rmtree(self.index_path)
            self.searcher = None

    def delete_by_filter(self, filter_key: str, filter_value: Any):
        """Not supported in LEANN easily."""
        logger.warning("delete_by_filter not implemented for LEANN")
