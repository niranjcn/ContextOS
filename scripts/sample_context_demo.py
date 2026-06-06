"""Sample end-to-end demo for ContextOS.

This script lives under scripts/ so the repo root stays focused on the product
code, tests, and packaging metadata.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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

SAMPLE_DOCUMENTS: dict[str, str] = {
    "meeting_notes_oct14.txt": """
Project Phoenix — Meeting Notes — October 14, 2024
Attendees: Arjun (project lead), Priya (backend dev), Rahul (design), Meera (QA)
Decisions made today:

Database: We chose PostgreSQL over MongoDB. Reason: our team knows SQL well,
and we need strong ACID guarantees for financial transactions.
API style: REST (not GraphQL). Reason: simpler for the mobile team to consume.
Launch date: January 15, 2025. Non-negotiable, tied to investor demo.
Hosting: AWS us-east-1. Reason: lowest latency for our US customer base.

Action items:

Arjun: Set up GitHub repo and CI/CD by Oct 21
Priya: Write database schema document by Oct 18
Rahul: Complete wireframes by Oct 28
Meera: Write test plan by Oct 25

Next meeting: October 21, same time.
""",
    "vendor_evaluation_sep24.txt": """
Vendor Evaluation Report — Cloud Storage — September 2024
Evaluated by: Arjun, Finance team
Vendors evaluated: AWS S3, Google Cloud Storage, Backblaze B2, Wasabi
WINNER: Backblaze B2
Reason for choosing Backblaze B2:

Price: $0.006/GB/month vs AWS S3 at $0.023/GB — 4x cheaper
S3-compatible API means we can switch later without rewriting code
No egress fees for the first 3x storage amount per month
Support team responded to our trial questions within 2 hours

Rejected vendors:

AWS S3: Too expensive at our projected 50TB/month scale
Google Cloud Storage: Requires Google Cloud account, creates vendor lock-in
Wasabi: No free trial, couldn't evaluate properly

Decision approved by finance on September 18, 2024.
""",
    "priya_email_thread.txt": """
Email thread: Re: Database schema review
From: Priya priya@phoenix.com
To: Arjun arjun@phoenix.com
Date: October 17, 2024
Arjun,
Attached is the initial database schema. Key decisions I made:

Used UUID as primary keys (not auto-increment integers) for security
Created separate tables for users, transactions, and audit_log
Added soft-delete columns (deleted_at) instead of hard deletes

One concern: the transactions table could get very large. I'm proposing we
partition it by month. Can we discuss this in the next meeting?
Also, Rahul mentioned his wireframes will be delayed by 3 days (now Oct 31).
Priya

From: Arjun arjun@phoenix.com
To: Priya priya@phoenix.com
Date: October 18, 2024
Priya,
Schema looks good. Approve the UUID decision — agreed on security grounds.
Partitioning: yes, let's discuss Monday. Good call raising it early.
Re Rahul's delay: acceptable, it doesn't block us. Updated the schedule.
New deadline for Rahul: October 31.
Arjun
""",
    "competitor_research.txt": """
Competitor Research — November 2024
Author: Arjun
Direct competitors to Project Phoenix:

FinanceTrack Pro

Market leader, 500k users
Weakness: mobile app is clunky, last updated 2022
Price: $49/month per user
We can beat them on mobile UX and price


ClearBooks

Strong in UK market, weak in US
Good API but no real-time sync
Price: $35/month per user
We can beat them with real-time features


MoneyMind

AI-powered features but privacy concerns (data sold to advertisers)
Price: free tier + $25/month premium
We can beat them with our privacy-first approach



Our differentiator: mobile-first, real-time sync, privacy-first, 30% cheaper.
Target launch price: $29/month per user.
""",
    "team_directory.txt": """
Project Phoenix — Team Directory
Arjun Kumar — Project Lead
Email: arjun@phoenix.com
Responsible for: overall architecture, stakeholder management, CI/CD setup
Based in: Bangalore
Priya Nair — Backend Developer
Email: priya@phoenix.com
Responsible for: API development, database design, server infrastructure
Based in: Kochi
Rahul Sharma — Product Designer
Email: rahul@phoenix.com
Responsible for: UI/UX design, wireframes, user research
Based in: Mumbai
Meera Iyer — QA Engineer
Email: meera@phoenix.com
Responsible for: test plans, QA automation, release sign-off
Based in: Chennai
""",
}

TEST_QUESTIONS = [
    ("Database decision", "Why did we choose PostgreSQL instead of MongoDB?"),
    ("Vendor choice", "Why was Backblaze B2 chosen over AWS S3?"),
    ("Person lookup", "What is Priya responsible for and where is she based?"),
    ("Action items", "What are Rahul's current deadlines?"),
    ("Budget research", "What is our planned pricing for Project Phoenix?"),
    ("Email content", "What concern did Priya raise about the database schema?"),
    ("Competitor", "What are the weaknesses of FinanceTrack Pro?"),
    (
        "Cross-document",
        "Summarize everything related to Priya across all documents.",
    ),
]


def build_pipeline() -> tuple[IngestionPipeline, VectorStore]:
    graph_store = GraphStore()
    vector_store = VectorStore()
    metadata_store = MetadataStore()
    pipeline = IngestionPipeline(vector_store, graph_store, metadata_store)
    return pipeline, vector_store


def build_engine() -> ContextEngine:
    graph_store = GraphStore()
    vector_store = VectorStore()
    retriever = HybridRetriever(graph_store, vector_store)
    prompt_builder = PromptBuilder()
    return ContextEngine(retriever, prompt_builder)


def main() -> None:
    console.print(
        Panel.fit(
            "[bold]ContextOS — Sample Data Demo[/bold]\n"
            "Ingesting 5 realistic documents, then asking 8 questions.\n"
            "No Gmail or cloud needed.",
            border_style="blue",
        )
    )

    console.print("\n[yellow]Preparing stores...[/yellow]")
    pipeline, vector_store = build_pipeline()
    engine = build_engine()

    console.print("[yellow]Ingesting sample documents...[/yellow]")
    total_chunks = 0
    for filename, content in SAMPLE_DOCUMENTS.items():
        result = pipeline.process_text(
            text=content,
            doc_id=filename,
            source=filename,
            metadata={"title": filename},
        )
        if result["status"] == "success":
            total_chunks += result["chunks_created"]

    console.print(
        f"\n[green]✓ Ingested {len(SAMPLE_DOCUMENTS)} documents → {total_chunks} chunks[/green]"
    )
    console.print(f"[dim]Vector store now has {vector_store.count()} total chunks[/dim]\n")

    if not engine.is_ready():
        console.print(
            "[red]Ollama not ready. Open Ollama and load a model before running queries.[/red]"
        )
        return

    console.print("[green]✓ Ollama connected[/green]\n")
    console.print("[yellow]Running test queries...[/yellow]\n")

    results_table = Table(
        "Test",
        "Question",
        "Answer (truncated)",
        "Time",
        show_header=True,
        header_style="bold",
    )

    passed = 0
    for test_name, question in TEST_QUESTIONS:
        console.print(f"[bold cyan]Testing: {test_name}[/bold cyan]")
        console.print(f"[dim]Q: {question}[/dim]")

        response = engine.query(question)
        short_answer = (
            response.answer[:120] + "..."
            if len(response.answer) > 120
            else response.answer
        )
        time_str = f"{response.inference_time_ms}ms"

        console.print(f"[green]A:[/green] {response.answer}\n")
        console.print(f"[dim]Sources: {', '.join(response.sources)} | {time_str}[/dim]\n")
        console.print("─" * 60 + "\n")

        results_table.add_row(test_name, question[:40] + "...", short_answer, time_str)
        passed += 1

    console.print(results_table)
    console.print(
        Panel.fit(
            f"[bold green]All {passed}/{len(TEST_QUESTIONS)} queries completed[/bold green]\n"
            f"Vector store: {vector_store.count()} chunks\n"
            f"Documents: {len(SAMPLE_DOCUMENTS)} ingested",
            border_style="green",
        )
    )


if __name__ == "__main__":
    main()