"""
Adapter Factory Functions
Dynamic adapter selection based on configuration
"""

from typing import Union
from config.config import YaverConfig
from tools.graph.networkx_adapter import NetworkXAdapter
from utils.logger import get_logger

logger = get_logger(__name__)


def get_graph_adapter(config: YaverConfig) -> Union[NetworkXAdapter, any]:
    """
    Get graph database adapter based on configuration

    Args:
        config: Yaver configuration

    Returns:
        Graph adapter instance (NetworkX or Neo4j)
    """
    provider = config.graph_db.provider

    if provider == "networkx":
        logger.info(
            f"Using NetworkX graph database: {config.graph_db.networkx_persist_path}"
        )
        return NetworkXAdapter(config.graph_db.networkx_persist_path)

    elif provider == "neo4j":
        logger.info(f"Using Neo4j graph database: {config.neo4j.uri}")
        try:
            from neo4j import GraphDatabase

            # Create Neo4j adapter wrapper
            class Neo4jAdapter:
                def __init__(self, uri, user, password):
                    self.driver = GraphDatabase.driver(uri, auth=(user, password))
                    self.driver.verify_connectivity()

                def close(self):
                    self.driver.close()

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc_val, exc_tb):
                    self.close()

            return Neo4jAdapter(
                config.neo4j.uri, config.neo4j.user, config.neo4j.password
            )

        except ImportError:
            logger.error("neo4j package not installed. Install with: pip install neo4j")
            logger.warning("Falling back to NetworkX")
            return NetworkXAdapter(config.graph_db.networkx_persist_path)
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            logger.warning("Falling back to NetworkX")
            return NetworkXAdapter(config.graph_db.networkx_persist_path)

    else:
        logger.warning(f"Unknown graph provider: {provider}, using NetworkX")
        return NetworkXAdapter(config.graph_db.networkx_persist_path)


def get_vector_adapter(config: YaverConfig) -> Union[any, any]:
    """
    Get vector database adapter based on configuration

    Args:
        config: Yaver configuration

    Returns:
        Vector adapter instance (ChromaDB or Qdrant)
    """
    provider = config.vector_db.provider

    if provider == "chroma":
        logger.info(f"Using ChromaDB: {config.vector_db.chroma_persist_dir}")
        try:
            import chromadb
            from chromadb.config import Settings

            # Create ChromaDB client
            client = chromadb.Client(
                Settings(
                    persist_directory=config.vector_db.chroma_persist_dir,
                    anonymized_telemetry=False,
                )
            )

            return client

        except ImportError:
            logger.error(
                "chromadb package not installed. Install with: pip install chromadb"
            )
            logger.warning("Falling back to Qdrant")
            return _get_qdrant_adapter(config)
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            logger.warning("Falling back to Qdrant")
            return _get_qdrant_adapter(config)

    elif provider == "qdrant":
        return _get_qdrant_adapter(config)

    else:
        logger.warning(f"Unknown vector provider: {provider}, using ChromaDB")
        try:
            import chromadb
            from chromadb.config import Settings

            client = chromadb.Client(
                Settings(
                    persist_directory=config.vector_db.chroma_persist_dir,
                    anonymized_telemetry=False,
                )
            )
            return client
        except:
            return _get_qdrant_adapter(config)


def _get_qdrant_adapter(config: YaverConfig):
    """Internal helper to get Qdrant adapter"""
    logger.info(f"Using Qdrant: {config.qdrant.host}:{config.qdrant.port}")
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(host=config.qdrant.host, port=config.qdrant.port)
        return client

    except ImportError:
        logger.error(
            "qdrant-client package not installed. Install with: pip install qdrant-client"
        )
        raise
    except Exception as e:
        logger.error(f"Failed to connect to Qdrant: {e}")
        raise
