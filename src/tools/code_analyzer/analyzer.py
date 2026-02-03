"""
Main Code Analyzer
Orchestrates the analysis process: Traversing directories, parsing files, caching, and storing results.
"""
from pathlib import Path
from typing import List, Generator
import logging
import ast
from rich.progress import Progress

from .ast_parser import ASTParser
from .neo4j_adapter import Neo4jAdapter
from .cache_manager import CachingManager
from .models import FileAnalysis
from .import_resolver import ImportResolver
from .call_graph import CallGraphBuilder
from tools.git_analyzer import GitAnalyzer
from core.analysis_session import AnalysisSession
import config.config as cfg 

logger = logging.getLogger(__name__)

class CodeAnalyzer:
    """
    Main entry point for Deep Code Analysis.
    """
    
    def __init__(self, session_id: str, repo_path: Path):
        self.repo_path = repo_path.resolve()
        self.session_id = session_id
        
        # Components
        self.session = AnalysisSession(session_id)
        self.cache = CachingManager()
        self.parser = ASTParser()
        self.import_resolver = ImportResolver(self.repo_path)
        self.call_graph_builder = CallGraphBuilder()
        self.git_analyzer = GitAnalyzer(str(self.repo_path))
        
        # Initialize Neo4j (Lazy load or config based)
        self.neo4j_adapter = None  

    def connect_db(self, uri: str, auth: tuple):
        self.neo4j_adapter = Neo4jAdapter(uri, auth)
        self.neo4j_adapter.init_schema()

    def close(self):
        """Close database connection"""
        if self.neo4j_adapter:
            self.neo4j_adapter.close()

    def analyze_repository(self, incremental: bool = False):
        """
        Perform full analysis of the repository.
        """
        self.session.log_progress(f"Starting analysis of {self.repo_path}")
        
        # Get Current Commit Hash
        current_commit = self.git_analyzer.get_current_commit() or "HEAD"

        files = list(self._find_files())
        
        if incremental:
            # TODO: Better state tracking efficiently.
            # For now, simplistic approach: Ask git what changed since last indexed commit?
            # But we don't know the last indexed commit easily without querying DB.
            # So simpler: Only process files where cache.get_cached_analysis() returns None?
            # Actually, `get_cached_analysis` checks file hash. If hash changed, it returns None.
            # So our logic below ALREADY handles incremental parsing based on file content!
            # The only optimization `incremental` flag provides is skipping the `neo4j` writes for unchanged files
            # if we trust the cache to indicate "no change".
            
            # However, if we mean "git incremental", we might restrict `files` list.
            pass

        total_files = len(files)
        
        self.session.update_plan(f"# Task Plan\n\n- [ ] Analyze {total_files} files in {self.repo_path.name}\n")
        self.session.log_progress(f"Found {total_files} files to analyze")
        
        processed_count = 0
        
        with Progress() as progress:
            task = progress.add_task("[green]Analyzing...", total=total_files)
            
            for file_path in files:
                try:
                    # 1. Check Cache
                    # This relies on content hash
                    analysis = self.cache.get_cached_analysis(file_path)
                    
                    if not analysis:
                        # 2. Parse (Cache Miss)
                        analysis = self.parser.parse_file(file_path, self.repo_path)
                        
                        # Phase 2: Enrich with Calls and Imports
                        if analysis:
                            # Parse AST for calls
                            with open(file_path, "r", encoding="utf-8") as f:
                                tree = ast.parse(f.read(), filename=str(file_path))
                                analysis.calls = self.call_graph_builder.build(tree)
                            
                            # Resolve Imports
                            for imp in analysis.imports:
                                resolved = self.import_resolver.resolve_import(imp, file_path)
                                if resolved:
                                    imp_name = imp.module if imp.module else (imp.names[0] if imp.names else "")
                                    if imp_name:
                                        analysis.resolved_imports[imp_name] = str(resolved)

                            self.cache.save_analysis(file_path, analysis)
                    
                    # 3. Store in Neo4j (Nodes + Relationships)
                    # Optimization: If incremental=True and we hit cache, we MIGHT skip storing if we assume DB is in sync.
                    # But safest is to always ensure DB has it.
                    if analysis and self.neo4j_adapter:
                        self.neo4j_adapter.store_analysis(analysis, self.repo_path.name, commit_hash=current_commit)
                        
                    processed_count += 1
                    progress.advance(task)
                    
                except Exception as e:
                    self.session.log_error(f"Error processing {file_path}: {e}")
                    logger.error(f"Error processing {file_path}: {e}")

        self.session.log_progress(f"Completed analysis. Processed {processed_count}/{total_files} files.")
        self.session.log_finding("Analysis Complete", f"Successfully analyzed {processed_count} files.")
        
        if self.neo4j_adapter:
            self.neo4j_adapter.close()

    def _find_files(self) -> Generator[Path, None, None]:
        """Yield python files in repo, respecting gitignore (simple version)"""
        # TODO: Implement proper gitignore parsing
        # For now, simple walk + exclude hidden/.git
        for p in self.repo_path.rglob("*.py"):
            parts = p.parts
            if any(part.startswith(".") for part in parts) or "venv" in parts or "__pycache__" in parts:
                continue
            yield p
