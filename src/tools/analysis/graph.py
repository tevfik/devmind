"""
Graph Analysis Module
Extracted from git_analysis.py
"""

import logging
from typing import Dict, Any, List, Optional
from config.config import Neo4jConfig

logger = logging.getLogger("tools.analysis.graph")

try:
    from neo4j import GraphDatabase
except ImportError:
    GraphDatabase = None


class GraphIndexer:
    """Indexes code structure into Neo4j."""

    def __init__(self):
        self.config = Neo4jConfig()
        self.driver = None
        if GraphDatabase:
            try:
                self.driver = GraphDatabase.driver(
                    self.config.uri,
                    auth=(self.config.username, self.config.password),
                    encrypted=False,
                )
            except Exception as e:
                logger.error(f"Failed to connect to Neo4j: {e}")
        else:
            logger.warning("neo4j package not found")

    def close(self):
        if self.driver:
            self.driver.close()

    def index_repo(self, structure: List[Dict[str, Any]]):
        """Push parsed structure to Graph DB."""
        if not self.driver:
            return {"error": "No Neo4j connection"}

        with self.driver.session() as session:
            # Create constraints (optional but good)
            session.run(
                "CREATE CONSTRAINT IF NOT EXISTS FOR (f:File) REQUIRE f.name IS UNIQUE"
            )

            count = 0
            for file_info in structure:
                session.execute_write(self._create_file_nodes, file_info)
                count += 1

        return {"indexed_files": count}

    @staticmethod
    def _create_file_nodes(tx, file_info):
        # Create File Node
        query_file = """
        MERGE (f:File {name: $name})
        SET f.loc = $loc
        """
        tx.run(query_file, name=file_info["file"], loc=file_info.get("loc", 0))

        # Create Functions and Relationships
        for func in file_info.get("functions", []):
            query_func = """
            MERGE (fn:Function {name: $func_name, file: $file_name})
            MERGE (f:File {name: $file_name})
            MERGE (f)-[:DEFINES]->(fn)
            """
            tx.run(query_func, func_name=func, file_name=file_info["file"])

        # Create Classes
        for cls in file_info.get("classes", []):
            query_cls = """
            MERGE (c:Class {name: $cls_name, file: $file_name})
            MERGE (f:File {name: $file_name})
            MERGE (f)-[:DEFINES]->(c)
            """
            tx.run(query_cls, cls_name=cls, file_name=file_info["file"])

        # Create Imports (Simple dependency)
        for imp in file_info.get("imports", []):
            query_imp = """
            MERGE (f:File {name: $file_name})
            MERGE (i:Module {name: $imp_name})
            MERGE (f)-[:IMPORTS]->(i)
            """
            tx.run(query_imp, file_name=file_info["file"], imp_name=imp)

        # Create Calls
        for call in file_info.get("calls", []):
            query_call = """
            MATCH (caller:Function {name: $caller_name, file: $file_name})
            MERGE (callee {name: $callee_name})
            MERGE (caller)-[:CALLS]->(callee)
            """
            tx.run(
                query_call,
                caller_name=call["caller"],
                callee_name=call["callee"],
                file_name=file_info["file"],
            )


class ImpactAnalyzer:
    """Analyzes change impact using Neo4j Graph."""

    def __init__(self):
        self.config = Neo4jConfig()
        self.driver = None
        if GraphDatabase:
            try:
                self.driver = GraphDatabase.driver(
                    self.config.uri,
                    auth=(self.config.username, self.config.password),
                    encrypted=False,
                )
            except Exception as e:
                logger.error(f"Failed to connect to Neo4j for Impact Analysis: {e}")

    def generate_call_graph(
        self, repo_name: Optional[str] = None, limit: int = 200
    ) -> Dict[str, str]:
        """Generates a mermaid chart of the call graph."""
        if not self.driver:
            return {"error": "Neo4j connection missing"}

        with self.driver.session() as session:
            if repo_name:
                query = f"""
                MATCH (caller:Function {{repo_name: $repo_name}})-[:CALLS]->(callee:Function)
                RETURN caller.name as source, callee.name as target
                LIMIT {limit}
                """
                params = {"repo_name": repo_name}
            else:
                query = f"""
                MATCH (caller:Function)-[:CALLS]->(callee:Function)
                RETURN caller.name as source, callee.name as target
                LIMIT {limit}
                """
                params = {}

            results = session.run(query, parameters=params).data()  # type: ignore

            mermaid = ["graph TD"]
            for r in results:
                # Sanitization for mermaid
                src = r["source"].replace(" ", "_").replace(".", "_")
                tgt = r["target"].replace(" ", "_").replace(".", "_")
                mermaid.append(f"    {src} --> {tgt}")

            return {"mermaid": "\n".join(mermaid)}

    def analyze(self, target_name: str, depth: int = 2) -> Dict[str, Any]:
        """Find what depends on target_name."""
        if not self.driver:
            return {"error": "Neo4j connection missing"}

        with self.driver.session() as session:
            # 1. Direct callers (Functions calling target)
            query_direct = """
            MATCH (caller:Function)-[:DEFINES|CALLS]->(target {name: $name})
            RETURN caller.name as caller, caller.file as file
            """
            direct_deps = session.run(query_direct, name=target_name).data()  # type: ignore

            # 2. Files importing target (if target is a module/file concept)
            query_imports = """
            MATCH (f:File)-[:IMPORTS]->(m:Module {name: $name})
            RETURN f.name as file
            """
            import_deps = session.run(query_imports, name=target_name).data()  # type: ignore

            # 3. Transitive impact (simplified)
            # Find chains: (Something) -> ... -> (Target)
            query_transitive = f"""
            MATCH path = (source)-[:CALLS*1..{depth}]->(target {{name: $name}})
            RETURN source.name as source, length(path) as hops
            """
            transitive_deps = session.run(query_transitive, name=target_name).data()  # type: ignore

            affected_files = set()
            for d in direct_deps:
                affected_files.add(d["file"])
            for i in import_deps:
                affected_files.add(i["file"])

            return {
                "target": target_name,
                "direct_dependents": direct_deps,
                "importers": import_deps,
                "transitive_count": len(transitive_deps),
                "affected_files": list(affected_files),
                "risk_level": "High" if len(affected_files) > 5 else "Low",
            }
