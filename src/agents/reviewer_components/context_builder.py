"""
Context Builder for Reviewer Agent.
Retrieves relevant context (RAG, Graph) for the review.
"""
import logging
from typing import List, Optional
from agents.agent_base import retrieve_relevant_context

logger = logging.getLogger("reviewer.context")


class ContextBuilder:
    """Builds context for the LLM review prompt."""

    def build_context(
        self, file_path: str, code_snippet: str, scanner_findings: List[str] = None
    ) -> str:
        """Constructs the prompt context section."""
        context = ""

        # 1. Scanner Findings Injection
        if scanner_findings:
            logger.debug(
                f"Injecting {len(scanner_findings)} scanner findings into context."
            )
            context += (
                "\n\n### Automated Analysis Findings:\n"
                + "\n".join(scanner_findings)
                + "\n"
            )

        # 2. Structural/RAG Context Retrieval
        if file_path:
            try:
                retrieved = retrieve_relevant_context(
                    f"File: {file_path}\nCode: {code_snippet[:500]}", limit=2
                )
                if retrieved:
                    context += f"\n\n### Structural Context:\n{retrieved}"
                    logger.info(f"Retrieved context length: {len(retrieved)}")
            except Exception as e:
                logger.warning(f"Failed to retrieve context: {e}")

        return context

    def get_impact_analysis(self, file_name: str) -> str:
        """Retrieves impact/ripple effect analysis from context."""
        impact_msg = ""
        try:
            impact_ctx = retrieve_relevant_context(
                f"What depends on {file_name}?", limit=2
            )
            # Heuristic parsing of the retrieved context to find graph edges
            if "Structural Context" in impact_ctx:
                lines = [
                    l
                    for l in impact_ctx.split("\n")
                    if "->" in l or "CALLS" in l or "IMPORTS" in l
                ]
                if lines:
                    impact_msg = "Possible Ripple Effects:\n" + "\n".join(
                        [f"> {l}" for l in lines[:3]]
                    )
        except Exception as e:
            logger.warning(f"Impact analysis failed: {e}")

        return impact_msg
