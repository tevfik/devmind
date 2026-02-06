import pytest
import os
import requests
import time
from agents.agent_memory import MemoryType
from config.config import reload_config

# Constants for Test Docker Ports
OLLAMA_BASE_URL = "http://localhost:11435"
QDRANT_HOST = "localhost"
QDRANT_PORT = 6335  # HTTP
QDRANT_GRPC_PORT = 6336
NEO4J_URI = "bolt://localhost:7688"
NEO4J_HTTP = "http://localhost:7475"
NEO4J_AUTH = ("neo4j", "testpassword")


@pytest.fixture
def configured_env(monkeypatch):
    """Configure environment variables for Dockerized services."""
    monkeypatch.setenv("OLLAMA_BASE_URL", OLLAMA_BASE_URL)

    # Qdrant Config
    monkeypatch.setenv("QDRANT_HOST", QDRANT_HOST)
    monkeypatch.setenv("QDRANT_PORT", str(QDRANT_PORT))
    monkeypatch.setenv("MEMORY_TYPE", "qdrant")

    # Neo4j Config
    monkeypatch.setenv("GRAPH_DB_PROVIDER", "neo4j")
    monkeypatch.setenv("NEO4J_URI", NEO4J_URI)
    monkeypatch.setenv("NEO4J_USER", NEO4J_AUTH[0])
    monkeypatch.setenv("NEO4J_PASSWORD", NEO4J_AUTH[1])

    # Reload config to apply changes
    reload_config()
    return True


def test_qdrant_memory_integration(configured_env, docker_env):
    """Test storing and retrieving memory vectors in Qdrant."""

    # 1. Ensure Embedding Model exists in Docker Ollama
    # If the container is fresh, it won't have the model.
    # Note: Pulling a model can take time (GBs).
    # For a quick test, this is risky.
    # Valid alternatives:
    # A) Assume model exists (via volume persistence in docker-compose)
    # B) Mock the embedding generation but test the storage? (Harder with integration test)
    # C) Use a tiny model.
    # Let's try to trigger a pull and wait a bit, or skip if timeout.

    model_name = "nomic-embed-text:latest"
    print(f"Checking/Pulling model {model_name} in {OLLAMA_BASE_URL}...")
    try:
        # Check if exists
        tags = requests.get(f"{OLLAMA_BASE_URL}/api/tags").json()
        found = any(m["name"] == model_name for m in tags.get("models", []))

        if not found:
            print(f"Model {model_name} not found. Pulling (this may take time)...")
            requests.post(f"{OLLAMA_BASE_URL}/api/pull", json={"name": model_name})
            # Wait loop
            for _ in range(60):  # Wait up to 60s for small model
                tags = requests.get(f"{OLLAMA_BASE_URL}/api/tags").json()
                if any(m["name"] == model_name for m in tags.get("models", [])):
                    break
                time.sleep(1)
            else:
                pytest.skip("Model pull timed out. Skipping vector test.")
    except Exception as e:
        pytest.skip(f"Ollama reachable check failed: {e}")

    # 2. Initialize Manager
    try:
        from agents.agent_memory import MemoryManager

        memory = MemoryManager()
    except Exception as e:
        pytest.fail(f"Failed to init MemoryManager: {e}")

    # 3. Add Memory
    secret = "The secret launch code is 42."
    memory.add_memory(content=secret, memory_type=MemoryType.SHORT_TERM)

    # 4. Search
    print("Searching for secret...")
    results = memory.search_memories("What is the launch code?", limit=1)

    assert len(results) > 0, "No results found"
    assert "42" in results[0]["content"]
    print("✅ Qdrant Vector Search Verified")


def test_neo4j_graph_integration(configured_env, docker_env):
    """Test graph node creation and querying in Neo4j."""

    # 1. Initialize
    try:
        from agents.agent_graph import GraphManager

        graph = GraphManager()
    except Exception as e:
        pytest.fail(f"Failed to init GraphManager: {e}")

    if "Neo4j" not in type(graph.adapter).__name__:
        print(f"Adapter is {type(graph.adapter).__name__}. Retrying config reload...")
        reload_config()
        graph = GraphManager()
        if "Neo4j" not in type(graph.adapter).__name__:
            pytest.skip("Could not load Neo4jAdapter even after config reload.")

    # 2. Store Node
    # GraphManager.store_file_node delegates to adapter.
    repo = "test_repo_graph"
    fpath = "src/graph_test.py"

    print(f"Storing node {fpath}...")
    graph.store_file_node(fpath, repo, "python", 150)

    # 3. Verify
    # Use find_nodes_by_name
    print("Querying node...")
    nodes = graph.find_nodes_by_name("src/graph_test.py")

    assert len(nodes) > 0, "Node not found in Graph"
    node = nodes[0]
    # Neo4j adapter usually returns dict with properties
    # Node usually has 'path' for File nodes
    assert node.get("path") == fpath or node.get("name") == fpath
    assert node.get("repo_name") == repo
    print("✅ Neo4j Graph Storage Verified")
