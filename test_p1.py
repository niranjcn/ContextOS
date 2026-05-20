# test_phase1.py
# Run this script to verify Phase 1 works end to end.
# Usage: python test_phase1.py

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core.ingestion.pipeline import IngestionPipeline
from core.inference.engine import ContextEngine
from core.inference.prompt_builder import PromptBuilder
from core.inference.retriever import HybridRetriever
from core.storage.graph import GraphStore
from core.storage.metadata import MetadataStore
from core.storage.vectors import VectorStore

console = Console()

def main():
    console.print(Panel.fit(
        "[bold]ContextOS — Phase 1 Test[/bold]\n"
        "Testing: ingest text → vector search → LLM answer",
        border_style="blue"
    ))

    # --- 1. Create the engine ---
    console.print("\n[yellow]Step 1:[/yellow] Starting engine...")
    graph_store = GraphStore()
    vector_store = VectorStore()
    metadata_store = MetadataStore()
    pipeline = IngestionPipeline(
        vector_store=vector_store,
        graph_store=graph_store,
        metadata_store=metadata_store,
    )
    retriever = HybridRetriever(graph_store=graph_store, vector_store=vector_store)
    prompt_builder = PromptBuilder()
    engine = ContextEngine(retriever=retriever, prompt_builder=prompt_builder)

    # --- 2. Check Ollama is reachable ---
    console.print("\n[yellow]Step 2:[/yellow] Checking Ollama connection...")
    if engine.is_ready():
        console.print("[green]✓ Ollama is running and model is available[/green]")
    else:
        console.print("[red]✗ Ollama not ready. Make sure Ollama is open and model is pulled.[/red]")
        return

    # --- 3. Ingest some sample text ---
    console.print("\n[yellow]Step 3:[/yellow] Ingesting sample documents...")

    sample_doc_1 = """
    Project Phoenix — Meeting Notes — October 14, 2024
    
    Attendees: Arjun (lead), Priya (backend), Rahul (design)
    
    Key decisions made:
    - We chose PostgreSQL over MongoDB for the main database because of its 
      strong consistency guarantees and our team's existing expertise.
    - The API will use REST (not GraphQL) for simplicity in the first version.
    - Target launch date is set for January 15, 2025.
    - Rahul will complete design mockups by October 28.
    
    Action items:
    - Arjun: Set up CI/CD pipeline by October 21
    - Priya: Write database schema by October 18
    - Rahul: Deliver mockups by October 28
    """

    sample_doc_2 = """
    Vendor Evaluation — Cloud Storage — September 2024
    
    We evaluated three vendors: AWS S3, Google Cloud Storage, and Backblaze B2.
    
    Final decision: We chose Backblaze B2 because:
    1. Cost is 6x cheaper than AWS S3 for our storage volume
    2. Compatible with the S3 API so migration is easy if needed
    3. Support team was responsive during our trial period
    
    AWS S3 was rejected due to cost. Google Cloud Storage was rejected because 
    it requires a Google Cloud account which creates vendor lock-in.
    """

    pipeline.process_text(
        text=sample_doc_1,
        doc_id="phase1_meeting_notes_oct14",
        source="meeting_notes_oct14.txt",
        metadata={"title": "Project Phoenix — Meeting Notes — October 14, 2024"},
    )
    pipeline.process_text(
        text=sample_doc_2,
        doc_id="phase1_vendor_eval_sep24",
        source="vendor_evaluation_sep24.txt",
        metadata={"title": "Vendor Evaluation — Cloud Storage — September 2024"},
    )

    # --- 4. Ask questions ---
    console.print("\n[yellow]Step 4:[/yellow] Running test queries...\n")

    questions = [
        "Why did we choose PostgreSQL?",
        "What is the launch date for Project Phoenix?",
        "Why was AWS S3 rejected as a vendor?",
        "What are Rahul's action items?",
    ]

    for question in questions:
        console.print(f"[bold cyan]Q: {question}[/bold cyan]")
        response = engine.query(question)

        console.print(f"[green]A:[/green] {response.answer}")

        # Show timing info
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_row("[dim]Sources[/dim]", f"[dim]{', '.join(response.sources)}[/dim]")
        table.add_row("[dim]Retrieval[/dim]", f"[dim]{response.retrieval_time_ms}ms[/dim]")
        table.add_row("[dim]Inference[/dim]", f"[dim]{response.inference_time_ms}ms[/dim]")
        console.print(table)
        console.print("─" * 60)

    console.print(Panel.fit(
        f"[bold green]Phase 1 complete![/bold green]\n"
        f"Vector store contains {vector_store.count()} chunks.",
        border_style="green"
    ))


if __name__ == "__main__":
    main()