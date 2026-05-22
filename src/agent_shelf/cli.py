"""CLI interface for agent-shelf."""

from __future__ import annotations

from pathlib import Path

import click
from dotenv import load_dotenv

load_dotenv()
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agent_shelf.router import AgentRouter

console = Console()
DEFAULT_AGENTS_DIR = Path("agents")


def get_router(agents_dir: str | None = None) -> AgentRouter:
    path = Path(agents_dir) if agents_dir else DEFAULT_AGENTS_DIR
    return AgentRouter(agents_dir=path)


@click.group()
@click.option("--agents-dir", default=None, help="Path to agents directory")
@click.pass_context
def main(ctx: click.Context, agents_dir: str | None) -> None:
    """agent-shelf: Convention-over-configuration AI agent framework."""
    ctx.ensure_object(dict)
    ctx.obj["agents_dir"] = agents_dir


@main.command()
@click.pass_context
def list(ctx: click.Context) -> None:
    """List all detected agents."""
    router = get_router(ctx.obj.get("agents_dir"))
    agents = router.scan()

    if not agents:
        console.print("[yellow]No agents found.[/yellow]")
        console.print(f"Create a directory under [bold]{DEFAULT_AGENTS_DIR}/[/bold] to get started.")
        return

    table = Table(title="Detected Agents")
    table.add_column("Name", style="bold cyan")
    table.add_column("Knowledge", justify="center")
    table.add_column("Skills", justify="center")
    table.add_column("Prompts", justify="center")

    for a in agents:
        table.add_row(
            a.name,
            "Yes" if a.has_knowledge else "-",
            "Yes" if a.has_skills else "-",
            "Yes" if a.has_prompts else "-",
        )

    console.print(table)


@main.command()
@click.argument("agent_name")
@click.pass_context
def run(ctx: click.Context, agent_name: str) -> None:
    """Start interactive chat with an agent."""
    router = get_router(ctx.obj.get("agents_dir"))
    info = router.get(agent_name)
    if info is None:
        console.print(f"[red]Agent '{agent_name}' not found.[/red]")
        return

    from agent_shelf.runtime import AgentRuntime

    console.print(Panel(f"Starting agent: [bold cyan]{agent_name}[/bold cyan]\nType 'exit' or 'quit' to end the session."))

    runtime = AgentRuntime(info)

    # Auto-index knowledge if available
    if info.has_knowledge:
        with console.status("Indexing knowledge base..."):
            count = runtime.index_knowledge()
        if count > 0:
            console.print(f"[dim]Indexed {count} chunks from knowledge base.[/dim]")

    while True:
        try:
            user_input = console.input("[bold green]You>[/bold green] ")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Session ended.[/dim]")
            break

        if user_input.strip().lower() in ("exit", "quit"):
            console.print("[dim]Session ended.[/dim]")
            break

        if not user_input.strip():
            continue

        with console.status("Thinking..."):
            try:
                result = runtime.chat(user_input)
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                continue

        # Show tool calls if any
        for tc in result.get("tool_calls", []):
            console.print(f"  [dim]Tool: {tc['skill']}({tc['arguments']}) -> {tc['result']}[/dim]")

        # Show sources if any
        sources = result.get("sources", [])
        if sources:
            src_names = list({s["source"] for s in sources})
            console.print(f"  [dim]Sources: {', '.join(src_names)}[/dim]")

        console.print(f"[bold blue]Agent>[/bold blue] {result['reply']}")


@main.command()
@click.argument("agent_name")
@click.argument("message")
@click.pass_context
def query(ctx: click.Context, agent_name: str, message: str) -> None:
    """Send a single query to an agent."""
    router = get_router(ctx.obj.get("agents_dir"))
    info = router.get(agent_name)
    if info is None:
        console.print(f"[red]Agent '{agent_name}' not found.[/red]")
        return

    from agent_shelf.runtime import AgentRuntime

    runtime = AgentRuntime(info)

    if info.has_knowledge:
        with console.status("Indexing knowledge base..."):
            runtime.index_knowledge()

    with console.status("Thinking..."):
        result = runtime.chat(message)

    console.print(result["reply"])


@main.command()
@click.argument("agent_name")
@click.pass_context
def index(ctx: click.Context, agent_name: str) -> None:
    """Re-index an agent's knowledge base."""
    router = get_router(ctx.obj.get("agents_dir"))
    info = router.get(agent_name)
    if info is None:
        console.print(f"[red]Agent '{agent_name}' not found.[/red]")
        return

    if not info.has_knowledge:
        console.print(f"[yellow]Agent '{agent_name}' has no knowledge/ directory.[/yellow]")
        return

    from agent_shelf.embeddings import create_embedding_adapter
    from agent_shelf.rag.engine import RAGEngine

    with console.status("Indexing..."):
        embedding = create_embedding_adapter()
        rag = RAGEngine(
            agent_name=agent_name,
            knowledge_dir=info.path / "knowledge",
            embedding_adapter=embedding,
        )
        count = rag.index()

    console.print(f"[green]Indexed {count} chunks for '{agent_name}'.[/green]")


@main.command()
@click.argument("agent_name")
@click.pass_context
def skills(ctx: click.Context, agent_name: str) -> None:
    """List skills for an agent."""
    router = get_router(ctx.obj.get("agents_dir"))
    info = router.get(agent_name)
    if info is None:
        console.print(f"[red]Agent '{agent_name}' not found.[/red]")
        return

    if not info.has_skills:
        console.print(f"[yellow]Agent '{agent_name}' has no skills/ directory.[/yellow]")
        return

    from agent_shelf.skills.executor import SkillExecutor

    executor = SkillExecutor(info.path / "skills")
    skill_list = executor.list_skills()

    if not skill_list:
        console.print("[yellow]No skills found.[/yellow]")
        return

    table = Table(title=f"Skills: {agent_name}")
    table.add_column("Name", style="bold cyan")
    table.add_column("Description")
    table.add_column("Parameters")

    for s in skill_list:
        params = ", ".join(s.parameters.get("properties", {}).keys())
        table.add_row(s.name, s.description, params or "-")

    console.print(table)
