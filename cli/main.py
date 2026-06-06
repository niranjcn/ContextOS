"""
ContextOS CLI — Typer-based terminal interface.

Provides commands for querying, ingesting, transcribing, drafting,
meeting briefs, decision search, graph exploration, connector management,
system health checks, and starting the API server.
"""

import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="contextos",
    help="ContextOS — Your private AI memory layer.",
    add_completion=False,
)
console = Console()


@app.command()
def query(
    question: str = typer.Argument(..., help="The question to ask ContextOS."),
) -> None:
    """Query the ContextOS engine with a natural language question."""
    from core.config import settings
    from core.inference.engine import ContextEngine
    from core.inference.prompt_builder import PromptBuilder
    from core.inference.retriever import HybridRetriever
    from core.storage.graph import GraphStore
    from core.storage.vectors import VectorStore

    with console.status("[bold green]Initializing engine..."):
        graph_store = GraphStore()
        vector_store = VectorStore()
        retriever = HybridRetriever(graph_store, vector_store)
        prompt_builder = PromptBuilder()
        engine = ContextEngine(retriever, prompt_builder)

    if not engine.is_ready():
        console.print(
            "[bold red]Error:[/] Ollama is not running. Start it with: ollama serve"
        )
        raise typer.Exit(1)

    with console.status("[bold green]Thinking..."):
        result = engine.query(question)

    console.print()
    console.print(Panel(result.answer, title="Answer", border_style="green"))

    if result.sources:
        console.print(f"\n[dim]Sources: {', '.join(result.sources)}[/]")
    console.print(
        f"[dim]Model: {result.model_used} | "
        f"Retrieval: {result.retrieval_time_ms}ms | "
        f"Inference: {result.inference_time_ms}ms[/]"
    )


@app.command()
def ingest(
    path: str = typer.Argument(..., help="Path to a file or folder to ingest."),
) -> None:
    """Ingest files from a path into the knowledge base."""
    from core.ingestion.pipeline import IngestionPipeline
    from core.storage.graph import GraphStore
    from core.storage.metadata import MetadataStore
    from core.storage.vectors import VectorStore
    from connectors.local_files import LocalFileConnector

    target = Path(path).resolve()
    if not target.exists():
        console.print(f"[bold red]Error:[/] Path not found: {target}")
        raise typer.Exit(1)

    with console.status("[bold green]Initializing stores..."):
        metadata_store = MetadataStore()
        graph_store = GraphStore()
        vector_store = VectorStore()
        pipeline = IngestionPipeline(vector_store, graph_store, metadata_store)

    if target.is_dir():
        connector = LocalFileConnector(watch_dir=target)
        with console.status(f"[bold green]Ingesting files from {target}..."):
            stats = connector.sync(metadata_store=metadata_store, pipeline=pipeline)
        table = Table(title="Ingestion Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", justify="right")
        table.add_row("Files Found", str(stats["fetched"]))
        table.add_row("New Ingested", str(stats["new"]))
        table.add_row("Skipped", str(stats["skipped"]))
        table.add_row("Errors", str(stats["errors"]))
        console.print(table)
    else:
        with console.status(f"[bold green]Ingesting {target.name}..."):
            result = pipeline.ingest_file(str(target))
        console.print(
            Panel(
                f"Status: {result['status']}\n"
                f"Chunks: {result['chunks_created']}",
                title=f"Ingested: {target.name}",
                border_style="green",
            )
        )


@app.command()
def transcribe(
    audio_path: str = typer.Argument(..., help="Path to audio file to transcribe."),
) -> None:
    """Transcribe an audio file and ingest the transcript."""
    from core.ingestion.pipeline import IngestionPipeline
    from core.storage.graph import GraphStore
    from core.storage.metadata import MetadataStore
    from core.storage.vectors import VectorStore
    from features.transcriber import MeetingTranscriber

    path = Path(audio_path).resolve()
    if not path.exists():
        console.print(f"[bold red]Error:[/] File not found: {path}")
        raise typer.Exit(1)

    with console.status("[bold green]Initializing..."):
        metadata_store = MetadataStore()
        graph_store = GraphStore()
        vector_store = VectorStore()
        pipeline = IngestionPipeline(vector_store, graph_store, metadata_store)
        transcriber = MeetingTranscriber()

    result = transcriber.transcribe_and_ingest(path, pipeline)
    t = result["transcription"]
    console.print(
        Panel(
            f"Language: {t.language}\n"
            f"Duration: {t.duration_seconds:.1f}s\n"
            f"Segments: {len(t.segments)}\n"
            f"Characters: {len(t.text)}",
            title=f"Transcribed: {path.name}",
            border_style="green",
        )
    )


@app.command()
def draft(
    instruction: str = typer.Argument(..., help="What to draft (e.g., 'Tell Priya the delivery is delayed')."),
    recipient: str = typer.Option("", help="Optional recipient name for context lookup."),
) -> None:
    """Generate a smart draft email or message in your writing voice."""
    from core.inference.engine import ContextEngine
    from core.inference.prompt_builder import PromptBuilder
    from core.inference.retriever import HybridRetriever
    from core.storage.graph import GraphStore
    from core.storage.vectors import VectorStore
    from features.smart_draft import SmartDraft

    with console.status("[bold green]Initializing engine..."):
        graph_store = GraphStore()
        vector_store = VectorStore()
        retriever = HybridRetriever(graph_store, vector_store)
        prompt_builder = PromptBuilder()
        engine = ContextEngine(retriever, prompt_builder)

    if not engine.is_ready():
        console.print("[bold red]Error:[/] Ollama is not running.")
        raise typer.Exit(1)

    with console.status("[bold green]Drafting..."):
        sd = SmartDraft(engine, retriever)
        result = sd.draft_content(topic=instruction, content_type="email")

    console.print()
    console.print(Panel(result.answer, title="Draft", border_style="cyan"))
    if result.sources:
        console.print(f"\n[dim]Context sources: {', '.join(result.sources)}[/]")


@app.command()
def brief(
    title: str = typer.Option(..., help="Meeting title."),
    attendees: str = typer.Option(..., help="Comma-separated attendee names."),
    date: str = typer.Option("", help="Meeting date/time string."),
    agenda: str = typer.Option("", help="Meeting agenda text."),
) -> None:
    """Generate a pre-meeting briefing with context about attendees."""
    from core.inference.engine import ContextEngine
    from core.inference.prompt_builder import PromptBuilder
    from core.inference.retriever import HybridRetriever
    from core.storage.graph import GraphStore
    from core.storage.vectors import VectorStore
    from features.meeting_brief import MeetingBrief

    participant_list = [a.strip() for a in attendees.split(",") if a.strip()]
    if not participant_list:
        console.print("[bold red]Error:[/] Provide at least one attendee.")
        raise typer.Exit(1)

    with console.status("[bold green]Initializing engine..."):
        graph_store = GraphStore()
        vector_store = VectorStore()
        retriever = HybridRetriever(graph_store, vector_store)
        prompt_builder = PromptBuilder()
        engine = ContextEngine(retriever, prompt_builder)

    if not engine.is_ready():
        console.print("[bold red]Error:[/] Ollama is not running.")
        raise typer.Exit(1)

    with console.status("[bold green]Generating brief..."):
        mb = MeetingBrief(engine, retriever)
        result = mb.generate_brief(
            title=title,
            participants=participant_list,
            date=date,
            agenda=agenda,
        )

    console.print()
    console.print(Panel(result.answer, title=f"Brief: {title}", border_style="magenta"))


@app.command()
def decisions(
    search_query: str = typer.Argument(
        "", help="Search query for decisions. Leave empty for recent."
    ),
    person: str = typer.Option("", help="Filter decisions by person name."),
    limit: int = typer.Option(10, help="Maximum results to return."),
) -> None:
    """Search or list decisions from the knowledge base."""
    from core.inference.retriever import HybridRetriever
    from core.storage.graph import GraphStore
    from core.storage.vectors import VectorStore
    from features.decision_log import DecisionLog

    with console.status("[bold green]Initializing..."):
        graph_store = GraphStore()
        vector_store = VectorStore()
        retriever = HybridRetriever(graph_store, vector_store)
        log = DecisionLog(retriever, vector_store)

    if person:
        results = log.get_decisions_by_person(person, k=limit)
    elif search_query:
        results = log.search_decisions(search_query, k=limit)
    else:
        results = log.get_recent_decisions(k=limit)

    if not results:
        console.print("[dim]No decisions found.[/]")
        return

    for i, d in enumerate(results, 1):
        content = d.get("content", "")[:200]
        source = d.get("source", "unknown")
        console.print(
            Panel(
                f"{content}{'...' if len(d.get('content', '')) > 200 else ''}",
                title=f"[{i}] {source}",
                border_style="yellow",
            )
        )


# ---- Graph subcommands ----

graph_app = typer.Typer(help="Explore the knowledge graph.")
app.add_typer(graph_app, name="graph")


@graph_app.command("people")
def graph_people() -> None:
    """List all people in the knowledge graph."""
    from core.storage.graph import GraphStore

    graph_store = GraphStore()
    people = graph_store.get_all_people()

    if not people:
        console.print("[dim]No people found in the graph.[/]")
        return

    table = Table(title="People in Knowledge Graph")
    table.add_column("#", style="dim", justify="right")
    table.add_column("Name", style="cyan")
    for i, name in enumerate(people, 1):
        table.add_row(str(i), name)
    console.print(table)


@graph_app.command("docs")
def graph_docs(
    limit: int = typer.Option(20, help="Maximum documents to show."),
) -> None:
    """List recent documents in the knowledge graph."""
    from core.storage.graph import GraphStore

    graph_store = GraphStore()
    docs = graph_store.get_recent_documents(limit=limit)

    if not docs:
        console.print("[dim]No documents in the graph.[/]")
        return

    table = Table(title="Recent Documents")
    table.add_column("Title", style="cyan")
    table.add_column("Source", style="green")
    table.add_column("Date", style="dim")
    for doc in docs:
        table.add_row(doc.get("title", ""), doc.get("source", ""), doc.get("date", ""))
    console.print(table)


@graph_app.command("stats")
def graph_stats() -> None:
    """Show knowledge graph statistics."""
    from core.storage.graph import GraphStore

    graph_store = GraphStore()
    stats = graph_store.get_stats()

    if not stats:
        console.print("[dim]No graph statistics available.[/]")
        return

    table = Table(title="Knowledge Graph Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", justify="right", style="green")
    for key, value in sorted(stats.items()):
        label = key.replace("_count", "").replace("_", " ").title()
        table.add_row(label, str(value))
    console.print(table)


# ---- Connector commands ----

@app.command()
def connect(
    connector_name: str = typer.Argument(
        ..., help="Connector to configure: gmail, gdrive"
    ),
) -> None:
    """Authenticate and configure a data connector (gmail, gdrive)."""
    if connector_name == "gmail":
        from connectors.gmail import GmailConnector

        c = GmailConnector()
        if not c.validate_config():
            console.print(
                "[bold red]Error:[/] Gmail not configured. "
                "Place client_secrets.json in your data directory."
            )
            raise typer.Exit(1)

        console.print("[bold green]Opening browser for Gmail OAuth...[/]")
        docs = c.fetch()
        console.print(f"[green]✓ Gmail connected. Found {len(docs)} emails.[/]")

    elif connector_name == "gdrive":
        from connectors.gdrive import GDriveConnector

        c = GDriveConnector()
        if not c.validate_config():
            console.print(
                "[bold red]Error:[/] Google Drive not configured. "
                "Place client_secrets.json in your data directory."
            )
            raise typer.Exit(1)

        console.print("[bold green]Opening browser for GDrive OAuth...[/]")
        docs = c.fetch()
        console.print(f"[green]✓ GDrive connected. Found {len(docs)} files.[/]")

    else:
        console.print(
            f"[bold red]Error:[/] Unknown connector '{connector_name}'. "
            "Available: gmail, gdrive"
        )
        raise typer.Exit(1)


@app.command()
def sync(
    source: str = typer.Option(
        "", help="Specific source to sync (gmail, gdrive, local_files, browser_history). "
        "Leave empty for all enabled."
    ),
) -> None:
    """Run connector sync to ingest new data from configured sources."""
    from core.ingestion.pipeline import IngestionPipeline
    from core.storage.graph import GraphStore
    from core.storage.metadata import MetadataStore
    from core.storage.vectors import VectorStore

    with console.status("[bold green]Initializing stores..."):
        metadata_store = MetadataStore()
        graph_store = GraphStore()
        vector_store = VectorStore()
        pipeline = IngestionPipeline(vector_store, graph_store, metadata_store)

    connectors_to_run = []

    if not source or source == "local_files":
        from connectors.local_files import LocalFileConnector
        c = LocalFileConnector()
        if c.validate_config():
            connectors_to_run.append(c)

    if not source or source == "gmail":
        try:
            from connectors.gmail import GmailConnector
            c = GmailConnector()
            if c.validate_config():
                connectors_to_run.append(c)
        except Exception:
            pass

    if not source or source == "gdrive":
        try:
            from connectors.gdrive import GDriveConnector
            c = GDriveConnector()
            if c.validate_config():
                connectors_to_run.append(c)
        except Exception:
            pass

    if not source or source == "browser_history":
        from connectors.browser_history import BrowserHistoryConnector
        c = BrowserHistoryConnector()
        if c.validate_config():
            connectors_to_run.append(c)

    if not connectors_to_run:
        console.print("[dim]No enabled connectors found.[/]")
        return

    table = Table(title="Sync Results")
    table.add_column("Connector", style="cyan")
    table.add_column("Fetched", justify="right")
    table.add_column("New", justify="right", style="green")
    table.add_column("Skipped", justify="right")
    table.add_column("Errors", justify="right", style="red")

    for c in connectors_to_run:
        with console.status(f"[bold green]Syncing {c._name}..."):
            stats = c.sync(metadata_store=metadata_store, pipeline=pipeline)
        table.add_row(
            c._name,
            str(stats["fetched"]),
            str(stats["new"]),
            str(stats["skipped"]),
            str(stats["errors"]),
        )

    console.print(table)


@app.command()
def status() -> None:
    """Show system health and status."""
    from core.config import settings
    from core.storage.metadata import MetadataStore
    from core.storage.vectors import VectorStore

    table = Table(title="ContextOS Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")

    # Ollama check
    try:
        import ollama as ollama_lib
        client = ollama_lib.Client(host=settings.OLLAMA_HOST)
        models = client.list()
        model_names = [m.get("name", m.get("model", "")) for m in models.get("models", [])]
        table.add_row("Ollama", f"✓ Running ({len(model_names)} models)")
        for name in model_names[:5]:
            table.add_row(f"  Model", name)
    except Exception:
        table.add_row("Ollama", "[red]✗ Not running[/]")

    # Metadata
    try:
        ms = MetadataStore()
        stats = ms.get_stats()
        table.add_row("Documents", f"✓ {stats['total']} processed")
    except Exception:
        table.add_row("Documents", "[red]✗ Error[/]")

    # Vectors
    try:
        vs = VectorStore()
        count = vs.count()
        table.add_row("Vectors", f"✓ {count} chunks")
    except Exception:
        table.add_row("Vectors", "[red]✗ Error[/]")

    table.add_row("Data Dir", str(settings.CONTEXTOS_DATA_DIR))
    table.add_row("DB Dir", str(settings.CONTEXTOS_DB_DIR))
    table.add_row("Encryption", "Enabled" if settings.ENABLE_ENCRYPTION else "Disabled")

    console.print(table)


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Host to bind to."),
    port: int = typer.Option(8000, help="Port to listen on."),
    reload: bool = typer.Option(False, help="Enable auto-reload."),
) -> None:
    """Start the ContextOS API server."""
    import uvicorn

    console.print(
        Panel(
            f"Starting ContextOS API server\n"
            f"URL: http://{host}:{port}\n"
            f"Docs: http://{host}:{port}/docs",
            title="ContextOS Server",
            border_style="green",
        )
    )
    uvicorn.run(
        "core.api.main:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    app()
