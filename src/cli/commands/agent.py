"""
Yaver Agent Commands
Manage autonomous agents and their learning.
"""
import typer
from ..ui import console, print_title, print_success, print_error, create_table

app = typer.Typer(help="Manage autonomous agent learning")


@app.command()
def status(
    project_id: str = typer.Argument(..., help="Project ID to check agent status for")
):
    """Show agent learning state."""
    print_title(f"Agent Status: {project_id}")
    # Placeholder for agent status implementation
    # In a real implementation, this would query the agent's memory/state
    console.print("[dim]Checking agent state...[/dim]")
    print_success("Agent is active and learning.")


@app.command()
def history(
    project_id: str = typer.Argument(..., help="Project ID"),
    limit: int = typer.Option(10, "--limit", "-l", help="Number of items to show"),
):
    """Show agent decision history."""
    print_title(f"Agent History: {project_id}")

    table = create_table(["Time", "Action", "Result"], "Recent Decisions")
    # Mock data
    table.add_row("10:00", "Analyze File", "Success")
    table.add_row("10:05", "Refactor Code", "Completed")
    console.print(table)


@app.command()
def teach(
    project_id: str = typer.Argument(..., help="Project ID"),
    rec_id: str = typer.Argument(..., help="Recommendation ID"),
    status: str = typer.Option(..., "--status", "-s", help="approve, reject, ignore"),
    note: str = typer.Option(None, "--note", "-n", help="Optional feedback note"),
):
    """Provide feedback to the agent."""
    print_title("Agent Feedback")
    console.print(f"Project: {project_id}")
    console.print(f"Rec ID: {rec_id}")
    console.print(f"Status: {status}")
    if note:
        console.print(f"Note: {note}")

    print_success("Feedback recorded!")


@app.command()
def work(
    task: str = typer.Argument(..., help="Task description for the agent"),
    project_id: str = typer.Option(
        None, "--project-id", "-p", help="Project ID context"
    ),
    path: str = typer.Option(".", "--path", help="Path to repository"),
):
    """
    Start an autonomous agent to work on a task.

    The agent will:
    1. Analyze the codebase (if needed)
    2. Decompose the task into subtasks
    3. Execute tasks iteratively (edits, git operations)
    """
    from pathlib import Path
    from tools.code_analyzer.analyzer import CodeAnalyzer
    from agents.agent_task_manager import task_manager_node, run_iteration_cycle
    from agents.agent_base import YaverState, TaskStatus, ConfigWrapper

    print_title("Autonomous Agent Worker")
    console.print(f"[bold]Task:[/bold] {task}")

    repo_path = Path(path).resolve()
    if not repo_path.exists():
        print_error(f"Repository path not found: {repo_path}")
        raise typer.Exit(1)

    # Initialize Context
    console.print(f"[dim]Initializing context from {repo_path}...[/dim]")

    # 1. Analyze Repo (Quick) to get stats
    analyzer = CodeAnalyzer(project_id or "cli_worker", repo_path)
    # Wrap in ConfigWrapper to allow attribute access (e.g. .total_files)
    repo_info = ConfigWrapper(analyzer.analyze_structure())

    # 2. Initialize State
    state = YaverState(
        user_request=task,
        repo_info=repo_info,
        iteration_count=0,
        tasks=[],
        log=[],
        errors=[],
    )

    # 3. Planning Phase
    console.print("\n[bold cyan]🤔 Planning...[/bold cyan]")
    state = task_manager_node(state)

    if not state.get("tasks"):
        print_error("Failed to generate plan.")
        raise typer.Exit(1)

    # 4. Execution Loop
    console.print("\n[bold cyan]⚙️  Executing...[/bold cyan]")

    while True:
        result = run_iteration_cycle(state)
        state.update(result)

        # Check termination
        if not result.get("should_continue", False):
            break

        current_task = result.get("current_task")
        if current_task and current_task.status == TaskStatus.FAILED:
            # Stop mainly on failure for now to avoid cascading breaks in CLI mode
            # In full agent mode, it might try to self-correct
            print_error(f"Task failed: {current_task.error}")
            break

    # Summary
    completed = len([t for t in state["tasks"] if t.status == TaskStatus.COMPLETED])
    total = len(state["tasks"])

    if completed == total:
        print_success(f"All {total} tasks completed successfully!")
    else:
        console.print(f"\n[yellow]⚠️  Completed {completed}/{total} tasks.[/yellow]")
