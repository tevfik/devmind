"""
Chat Agent Integration
Integrates RAG, Code Analysis, and LLM for interactive chat.
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict
import time

from rich.console import Console
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from tools.code_analyzer.analyzer import CodeAnalyzer
from tools.rag.rag_service import RAGService
from agents.agent_base import create_llm

logger = logging.getLogger(__name__)

class ChatAgent:
    """
    Intelligent Agent for DevMind Chat.
    Combines general LLM capabilities with RAG-based code knowledge.
    """
    
    def __init__(self, session_id: str, repo_path: str = ".", project_id: str = None):
        self.console = Console()
        self.session_id = session_id  # Chat session ID
        self.project_id = project_id  # Project ID for filtering repos in RAG
        self.repo_path = Path(repo_path)
        self.analyzer: Optional[CodeAnalyzer] = None
        self.rag_service: Optional[RAGService] = None
        self.history = []
        self._llm = None
        
        self._initialize_resources()
        
    def _initialize_resources(self):
        """Initialize Analyzer and RAG service."""
        try:
            self.console.print("[dim]Initializing Code Analysis Engine...[/dim]")
            
            # Initialize Code Analyzer
            self.analyzer = CodeAnalyzer(self.session_id, self.repo_path)
            
            # Connect to Neo4j (using default local config for now)
            # In a real scenario, we might prompt for these or read from .env if not set
            # For now, let's assume default localhost:7687
            try:
                self.analyzer.connect_db("bolt://localhost:7687", ("neo4j", "password"))
            except Exception as e:
                self.console.print(f"[yellow]Warning: Graph database not connected (Neo4j): {e}[/yellow]")

            # Initialize RAG
            self.console.print("[dim]Initializing Semantic Engine...[/dim]")
            try:
                self.analyzer.init_rag()
                self.rag_service = self.analyzer.rag_service
                self.console.print("[green]Ready![/green]")
            except Exception as rag_err:
                self.console.print(f"[yellow]Warning: RAG service initialization failed: {rag_err}[/yellow]")
                self.console.print("[dim]Continuing without semantic search capabilities[/dim]")
            
            # Initialize basic LLM for conversational parts
            self._llm = create_llm()
            
        except Exception as e:
            import traceback
            self.console.print(f"[red]Error initializing agent resources: {e}[/red]")
            self.console.print(f"[dim]{traceback.format_exc()}[/dim]")

    def chat(self, user_input: str) -> str:
        """
        Process a user message and return the response.
        Decides whether to use RAG or simple Chat.
        """
        self.history.append(HumanMessage(content=user_input))
        
        # Heuristic: If we have RAG service, let's use it for code queries
        # The RAG service already does intent classification.
        # But for "Hi", "Hello" etc, we might want to skip RAG overhead?
        # RAG service intent classifier should handle "Chat" intent too theoretically, 
        # but let's stick to our RAGService logic which returns "I couldn't find..." if not relevant,
        # or performs hybrid retrieval.
        
        response_text = ""
        
        if self.rag_service:
            # Enriched query using RAG with optional project filtering
            try:
                response_text = self.rag_service.answer(user_input, session_id=self.project_id)
            except Exception as e:
                self.console.print(f"[yellow]RAG Error: {e}[/yellow]")
                response_text = f"I encountered an error accessing the codebase knowledge: {e}"
        else:
            # Fallback to simple LLM
            try:
                resp = self._llm.invoke(user_input)
                response_text = resp.content if hasattr(resp, 'content') else str(resp)
            except Exception as e:
                response_text = f"Error: {e}"

        return response_text

    def close(self):
        if self.analyzer:
            self.analyzer.close()
