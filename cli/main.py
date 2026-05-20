"""
ContextOS CLI — Typer-based terminal interface.

Provides commands for querying, ingesting, transcribing, graph exploration,
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
        content = target.read_text(encoding="utf-8", errors="replace")
        import hashlib
        doc_id = hashlib.sha256(f"{target}".encode()).hexdigest()[:16]
        with console.status(f"[bold green]Ingesting {target.name}..."):
            result = pipeline.process_text(
                text=content,
                doc_id=f"cli_{doc_id}",
                source="cli_ingest",
                metadata={"filename": target.name, "filepath": str(target)},
            )
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
