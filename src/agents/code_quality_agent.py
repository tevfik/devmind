"""
Code Quality Autonomous Agent
Main orchestrator for code analysis, reasoning, and recommendations.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class CodeQualityAgent:
    """
    Autonomous agent for code quality analysis and recommendations.

    Workflow:
    1. Observe → Detect changes in repo
    2. Analyze → Gather metrics from Neo4j
    3. Evaluate → Use LLM to reason about issues
    4. Decide → Prioritize and rank recommendations
    5. Report → Generate human-readable report
    6. Execute → Optional automation or wait for approval
    7. Learn → Store feedback for future sessions
    """

    def __init__(self, project_id: str, neo4j_adapter, agent_base):
        """
        Initialize agent

        Args:
            project_id: Project identifier
            neo4j_adapter: Neo4j connection
            agent_base: Yaver agent (for LLM access)
        """
        self.project_id = project_id
        self.neo4j = neo4j_adapter
        self.agent = agent_base

        # State storage
        self.state_dir = Path.home() / ".yaver" / "projects" / project_id / "agent"
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self._load_state()

    def _load_state(self):
        """Load agent state from disk"""
        state_file = self.state_dir / "state.json"

        if state_file.exists():
            with open(state_file) as f:
                self.state = json.load(f)
        else:
            self.state = {
                "created_at": datetime.now().isoformat(),
                "last_analysis": None,
                "learned_preferences": {},
                "decision_history": [],
                "approved_suggestions": [],
                "rejected_suggestions": [],
            }

    def _save_state(self):
        """Save agent state to disk"""
        state_file = self.state_dir / "state.json"
        with open(state_file, "w") as f:
            json.dump(self.state, f, indent=2)

    def analyze_repository(self) -> Dict[str, Any]:
        """
        Full analysis workflow: Observe → Analyze → Evaluate → Decide → Report

        Returns:
            Comprehensive analysis report with recommendations
        """

        logger.info(f"[Agent] Starting analysis for {self.project_id}")

        # Step 1: OBSERVE
        logger.info("[Agent] OBSERVE: Checking repository changes")
        changes = self._observe_changes()

        # Step 2: ANALYZE
        logger.info("[Agent] ANALYZE: Gathering metrics")
        from tools.metrics import MetricsAnalyzer

        analyzer = MetricsAnalyzer(self.neo4j)
        metrics = analyzer.analyze_repository(self.project_id)

        # Enrich with real static analysis
        self._enrich_metrics(metrics)

        # Step 3: EVALUATE
        logger.info("[Agent] EVALUATE: Reasoning with LLM")
        from agents.decision_engine import DecisionEngine

        decision_engine = DecisionEngine(self.agent)
        decisions = decision_engine.reason_about_issues(metrics)

        # Step 4: DECIDE
        logger.info("[Agent] DECIDE: Prioritizing recommendations")
        prioritized = self._prioritize_with_learning(decisions)

        # Step 5: REPORT
        logger.info("[Agent] REPORT: Generating recommendations")
        report = self._generate_report(metrics, prioritized, changes)

        # Store analysis snapshot
        self._store_snapshot(report)
        self.state["last_analysis"] = datetime.now().isoformat()
        self._save_state()

        return report

    def _enrich_metrics(self, metrics: Dict[str, Any]):
        """
        Enrich metrics with real-time static analysis using MetricsManager.
        This provides accurate complexity scores (Radon/Lizard) vs Neo4j estimates.
        """
        from tools.metrics import MetricsManager, ComplexityMetric

        manager = MetricsManager()
        project_root = Path.cwd()

        # We will collect new complexity metrics
        real_metrics = []

        # Iterate over all files in repo
        # Optimization: In a real scenario, map this to files found in Neo4j to save IO
        for file_path in project_root.rglob("*"):
            if not file_path.is_file():
                continue
            if any(
                p in str(file_path)
                for p in [".git", "__pycache__", "venv", "node_modules"]
            ):
                continue

            result = manager.get_metrics(file_path)
            complexity_data = result.get("complexity")
            lines_data = result.get("lines", {})

            if complexity_data:
                # Add complex functions found by Radon/Lizard
                complex_funcs = complexity_data.get("complex_functions", [])
                for func in complex_funcs:
                    # func is typically {'name': '...', 'complexity': N, 'lineno': ...}
                    # We adapt this to the ComplexityMetric dataclass
                    metric = ComplexityMetric(
                        function_id=f"{file_path.name}:{func['name']}",
                        function_name=func["name"],
                        file_path=str(file_path.relative_to(project_root)),
                        complexity_score=float(func["complexity"]),
                        loc=0,  # Detail not always avail in summary
                        parameters=0,
                        has_docstring=False,
                    )
                    real_metrics.append(metric)

        # If we found real metrics, replace or merge with Neo4j estimate
        if real_metrics:
            logger.info(
                f"[Agent] Enriched metrics with {len(real_metrics)} functions from Static Analysis"
            )
            # We prioritize real analysis.
            # Note: This might overwrite Neo4j measurements, which is desired as Neo4j
            # currently uses a specific approximation.
            metrics["complexity_metrics"] = real_metrics

            # Re-calculate quality score based on new numbers
            from tools.metrics import MetricsAnalyzer

            # Mocking analyzer just to access static calculation method if it was static?
            # It's an instance method. Let's just create a temp one or copy logic.
            # actually we can just re-use the analyzer instance from the caller if we passed it,
            # but simpler to just instantiate light wrapper since logic is pure math.
            # Or manually update the score dict.

            # Recalculate summary stats
            high_complexity = [m for m in real_metrics if m.complexity_score > 10]
            metrics["summary"]["high_complexity_count"] = len(high_complexity)
            metrics["summary"]["total_functions"] = len(real_metrics)
            if real_metrics:
                avg = sum(m.complexity_score for m in real_metrics) / len(real_metrics)
                metrics["summary"]["avg_complexity"] = round(avg, 1)

    def _observe_changes(self) -> Dict[str, Any]:
        """Detect changes since last analysis"""

        from core.git_helper import GitHelper

        git = GitHelper(Path.cwd())

        changes = {
            "current_commit": git.get_current_commit(),
            "previous_commit": self.state.get("last_analyzed_commit"),
            "files_changed": 0,
        }

        if (
            changes["previous_commit"]
            and changes["current_commit"] != changes["previous_commit"]
        ):
            changed_files = git.get_changed_files(changes["previous_commit"])
            changes["files_changed"] = len(changed_files)
            changes["files_list"] = changed_files

        return changes

    def _prioritize_with_learning(self, decisions: List) -> List:
        """Adjust priorities based on learned preferences"""

        prefs = self.state.get("learned_preferences", {})

        for decision in decisions:
            # Check if user has pattern of approving/rejecting this type
            issue_type = decision.issue_type

            if issue_type in prefs:
                preference_score = prefs[issue_type]
                if preference_score > 0:
                    # User likes this type of suggestion
                    decision.priority = min(10, decision.priority + 1)
                elif preference_score < 0:
                    # User dislikes this type
                    decision.priority = max(1, decision.priority - 1)

        return sorted(decisions, key=lambda d: (-d.priority, d.issue_type))

    def _generate_report(
        self, metrics: Dict, decisions: List, changes: Dict
    ) -> Dict[str, Any]:
        """Generate human-readable analysis report"""
        from dataclasses import asdict, is_dataclass

        def to_dict(obj):
            if is_dataclass(obj):
                return asdict(obj)
            if isinstance(obj, list):
                return [to_dict(x) for x in obj]
            if isinstance(obj, dict):
                return {k: to_dict(v) for k, v in obj.items()}
            return obj

        summary = metrics.get("summary", {})
        quality = metrics.get("quality_score")

        report = {
            "timestamp": datetime.now().isoformat(),
            "project_id": self.project_id,
            "repository_health": {
                "quality_score": quality.total_score if quality else 0,
                "status": summary.get("health", "unknown"),
                "total_functions": summary.get("total_functions", 0),
                "high_complexity_count": summary.get("high_complexity_count", 0),
                "dead_code_count": summary.get("dead_code_count", 0),
                "circular_deps": summary.get("circular_deps_count", 0),
            },
            "changes": changes,
            "metrics": to_dict(metrics),
            "recommendations": [],
        }

        # Format decisions as recommendations
        for i, decision in enumerate(decisions, 1):
            report["recommendations"].append(
                {
                    "rank": i,
                    "priority": decision.priority,
                    "type": decision.issue_type,
                    "title": decision.title,
                    "description": decision.description,
                    "reasoning": decision.reasoning,
                    "action": decision.recommended_action,
                    "effort": decision.effort_estimate,
                    "risk": decision.risk_level,
                    "autofix_available": decision.can_autofix,
                }
            )

        return report

    def _store_snapshot(self, report: Dict):
        """Store analysis snapshot for tracking"""

        analysis_dir = self.state_dir / "analyses"
        analysis_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_file = analysis_dir / f"{timestamp}_analysis.json"

        with open(snapshot_file, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"Stored analysis snapshot: {snapshot_file}")

    def record_user_feedback(self, recommendation_id: str, feedback: str):
        """
        Learn from user feedback

        Args:
            recommendation_id: Which recommendation
            feedback: "approved", "rejected", "done"
        """

        # This would be populated from chat interaction
        # For now, just track it
        feedback_entry = {
            "timestamp": datetime.now().isoformat(),
            "recommendation_id": recommendation_id,
            "feedback": feedback,
        }

        self.state["decision_history"].append(feedback_entry)

        if feedback == "approved":
            self.state["approved_suggestions"].append(recommendation_id)
        elif feedback == "rejected":
            self.state["rejected_suggestions"].append(recommendation_id)

        self._save_state()

    def get_agent_status(self) -> Dict[str, Any]:
        """Get current agent status"""

        return {
            "project_id": self.project_id,
            "created_at": self.state.get("created_at"),
            "last_analysis": self.state.get("last_analysis"),
            "learned_preferences": self.state.get("learned_preferences"),
            "total_recommendations_made": len(self.state.get("decision_history", [])),
            "suggestions_approved": len(self.state.get("approved_suggestions", [])),
            "suggestions_rejected": len(self.state.get("rejected_suggestions", [])),
        }
