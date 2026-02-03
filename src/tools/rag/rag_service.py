"""
RAG Service
Combines Graph retrieval (Neo4j) and Vector retrieval (Qdrant) to answer questions about the codebase.
"""

import logging
from typing import List, Dict, Any, Optional
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from src.config.config import OllamaConfig
from tools.code_analyzer.neo4j_adapter import Neo4jAdapter
from tools.code_analyzer.qdrant_adapter import QdrantAdapter
from tools.code_analyzer.embeddings import CodeEmbedder

logger = logging.getLogger(__name__)

class RAGService:
    """
    Retrieval Augmented Generation Service for Codebase.
    """

    def __init__(
        self, 
        neo4j_adapter: Neo4jAdapter,
        qdrant_adapter: QdrantAdapter,
        code_embedder: CodeEmbedder,
        config: Optional[OllamaConfig] = None
    ):
        self.neo4j = neo4j_adapter
        self.qdrant = qdrant_adapter
        self.embedder = code_embedder
        self.config = config or OllamaConfig()
        
        self.llm = ChatOllama(
            base_url=self.config.base_url,
            model=self.config.model_general,
            temperature=0.2
        )
        
        # Prompts
        self._init_prompts()

    def _init_prompts(self):
        """Initialize LangChain prompts."""
        
        # Intent Classification
        self.intent_prompt = ChatPromptTemplate.from_template(
            """
            You are a query analyzer for a code analysis tool.
            Analyze the user's question and determine the best retrieval strategy.
            
            Question: {question}
            
            Return ONLY one of the following labels:
            - STRUCTURE: Question about class hierarchy, function calls, dependencies, files. (e.g., "What calls X?", "Show architecture")
            - SEMANTIC: Question about meaning, logic, specific implementation details, explanation of code. (e.g., "How does authentication work?", "Find code that validates emails")
            - HYBRID: Requires both. (e.g., "Explain the login flow and list all files involved")
            
            Label:
            """
        )
        
        # Code Explanation
        self.qa_prompt = ChatPromptTemplate.from_template(
            """
            You are an expert software architect answering questions about the current codebase.
            Use the provided Context to answer the Question.
            
            Context (Structure + Code):
            {context}
            
            Question: {question}
            
            Answer concisely and cite files or functions where appropriate.
            """
        )

    def retrieve_context(self, question: str, strategy: str = "HYBRID") -> str:
        """
        Retrieve relevant context based on strategy.
        """
        context_parts = []
        
        # 1. Structural Retrieval (Neo4j)
        if strategy in ["STRUCTURE", "HYBRID"]:
            # TODO: Implement Text-to-Cypher or specific keyword lookup
            # For now, simple keyword matching for "calls", "dependencies"
            # Or just generic neighbor search if entities are named
            pass
            
        # 2. Semantic Retrieval (Qdrant)
        if strategy in ["SEMANTIC", "HYBRID"]:
            try:
                query_vec = self.embedder.embed_query(question)
                results = self.qdrant.search(query_vec, limit=5, score_threshold=0.6)
                
                if results:
                    context_parts.append("--- RELEVANT CODE SNIPPETS ---")
                    for res in results:
                        payload = res.get('payload', {})
                        name = payload.get('name', 'Unknown')
                        file = payload.get('file_path', 'Unknown')
                        # Prefer 'content' (chunk text) over 'source' (raw code) to keep context concise but rich
                        text = payload.get('content', '') 
                        
                        context_parts.append(f"File: {file} | Symbol: {name}\n{text}\n")
            except Exception as e:
                logger.error(f"Semantic retrieval failed: {e}")
        
        return "\n".join(context_parts)

    def answer(self, question: str) -> str:
        """
        End-to-end RAG pipeline.
        """
        # 1. Determine Intent
        try:
            intent_chain = self.intent_prompt | self.llm | StrOutputParser()
            intent = intent_chain.invoke({"question": question}).strip()
            logger.info(f"Query Intent: {intent}")
        except Exception:
            intent = "HYBRID"
        
        # 2. Retrieve
        context = self.retrieve_context(question, strategy=intent)
        
        if not context.strip():
            return "I couldn't find relevant information in the codebase to answer that."
            
        # 3. Generate Answer
        qa_chain = self.qa_prompt | self.llm | StrOutputParser()
        response = qa_chain.invoke({"context": context, "question": question})
        
        return response
