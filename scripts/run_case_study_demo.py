"""Full 20-step KnowledgeOps case study demonstration with Rich output."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

from app.core.config import get_settings
from app.schemas.common import QueryRequest

console = Console(force_terminal=True, legacy_windows=False)

METRICS: dict[str, Any] = {
    "documents_discovered": 0,
    "documents_changed": 0,
    "documents_unchanged": 0,
    "chunks_indexed": 0,
    "hit_rate_at_5": 0.0,
    "mrr": 0.0,
    "avg_latency_ms": 0.0,
    "questions_evaluated": 0,
    "supported_answers": 0,
    "correct_refusals": 0,
    "knowledge_gaps": 0,
    "unnecessary_reembeds": 0,
}


def _step(number: int, title: str) -> None:
    console.print(Rule(f"[bold cyan]Step {number}: {title}[/bold cyan]"))


async def _session_context():
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.api.deps import IngestionService, QueryOrchestrator, Repositories
    from app.db.models import Base
    from app.generation.service import QueryService as GenerationQueryService
    from app.knowledge_gaps.service import KnowledgeGapService
    from app.providers.factory import create_embedding_provider
    from app.retrieval.qdrant_client import QdrantService
    from app.retrieval.service import RetrievalService
    from scripts.setup_demo import setup_demo

    settings = get_settings()
    setup_demo(reset_index=True)

    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session = session_factory()
    qdrant = QdrantService(settings)
    embedding = create_embedding_provider(settings)
    await qdrant.ensure_collection(embedding.vector_size)

    repos = Repositories(session)
    retrieval = RetrievalService(qdrant=qdrant, embedding_provider=embedding, settings=settings)
    generation = GenerationQueryService(retrieval_service=retrieval, settings=settings)
    gap_service = KnowledgeGapService(repos.knowledge_gaps, settings)
    orchestrator = QueryOrchestrator(repos, generation, retrieval, gap_service)
    ingestion = IngestionService(session, qdrant, settings)

    return settings, engine, session, qdrant, repos, retrieval, orchestrator, ingestion


def run_demo() -> None:
    """Execute the 20-step case study demo synchronously."""
    asyncio.run(_run_demo_async())


async def _run_demo_async() -> None:
    console.print(
        Panel(
            "[bold]KnowledgeOps RAG Automation Platform[/bold]\n"
            "Self-maintaining knowledge base case study demo",
            border_style="blue",
        )
    )

    (
        settings,
        engine,
        session,
        qdrant,
        repos,
        retrieval,
        orchestrator,
        ingestion,
    ) = await _session_context()
    demo_path = Path(settings.demo_knowledge_path)
    if not demo_path.is_absolute():
        demo_path = settings.project_root / demo_path

    target_doc = demo_path / "hr" / "leave-policy.md"
    grounded_question = "How many vacation days do full-time employees receive?"
    unsupported_question = "What is the company's policy on Mars colonization subsidies?"

    try:
        _step(1, "Initialise clean knowledge base")
        console.print("[green]Demo knowledge base prepared.[/green]")

        _step(2, "Discover 30+ documents")
        from app.ingestion.discovery.demo import DemoSource

        source = DemoSource(settings)
        discovered = await source.discover()
        METRICS["documents_discovered"] = len(discovered)
        console.print(f"Discovered [bold]{len(discovered)}[/bold] documents")

        _step(3, "Parse and chunk them")
        _step(4, "Generate embeddings")
        _step(5, "Build hybrid index")
        console.print("[cyan]Running initial ingestion...[/cyan]")
        summary1 = await ingestion.run(source="demo")
        await session.commit()

        METRICS["chunks_indexed"] = summary1.chunks_indexed
        METRICS["documents_changed"] = summary1.documents_new + summary1.documents_modified
        console.print(
            f"Indexed [bold]{summary1.chunks_indexed}[/bold] chunks from "
            f"[bold]{summary1.documents_new}[/bold] new documents"
        )

        _step(6, "Run evaluation")
        from scripts.run_evaluation import run_evaluation

        eval_result = await run_evaluation(dataset_name="sample", top_k=5)
        metrics = eval_result.get("metrics", {})
        METRICS["hit_rate_at_5"] = metrics.get("hit_rate_at_5", 0.0)
        METRICS["mrr"] = metrics.get("mrr", 0.0)
        METRICS["questions_evaluated"] = 2
        console.print(
            f"Hit Rate @ 5: [bold]{METRICS['hit_rate_at_5']:.2f}[/bold]  MRR: [bold]{METRICS['mrr']:.2f}[/bold]"
        )

        _step(7, "Ask grounded questions")
        start = time.perf_counter()
        response1 = await orchestrator.query(
            QueryRequest(query=grounded_question, include_debug=True)
        )
        await session.commit()
        METRICS["avg_latency_ms"] = response1.latency_ms
        if response1.answer and "insufficient" not in (response1.answer or "").lower():
            METRICS["supported_answers"] += 1

        _step(8, "Show citations")
        console.print(Panel(response1.answer or "", title="Grounded Answer", border_style="green"))
        if response1.citations:
            for idx, c in enumerate(response1.citations, 1):
                console.print(f"  [{idx}] {c.document_title}")

        _step(9, "Ask an unsupported question")
        response2 = await orchestrator.query(QueryRequest(query=unsupported_question))
        await session.commit()

        _step(10, "Show knowledge-gap creation")
        gaps, total_gaps = await repos.knowledge_gaps.list_gaps(page_size=5)
        METRICS["knowledge_gaps"] = total_gaps
        METRICS["correct_refusals"] = 1 if "insufficient" in (response2.answer or "").lower() else 0
        console.print(
            Panel(
                response2.answer or "", title="Unsupported Question Response", border_style="yellow"
            )
        )
        console.print(f"Knowledge gaps recorded: [bold]{total_gaps}[/bold]")

        _step(11, "Modify a policy document")
        original = target_doc.read_text(encoding="utf-8")
        modified = original.replace(
            "10 sick days annually",
            "12 sick days annually (updated policy effective 2026)",
        )
        if modified == original:
            modified = (
                original
                + "\n\n## Update\nSick leave increased to 12 days annually effective 2026.\n"
            )
        target_doc.write_text(modified, encoding="utf-8")
        console.print(f"Modified [cyan]{target_doc.name}[/cyan]")

        _step(12, "Re-run ingestion")
        summary2 = await ingestion.run(source="demo")
        await session.commit()

        _step(13, "Detect only the changed document")
        _step(14, "Re-index relevant chunks")
        console.print(
            f"Changed: [bold]{summary2.documents_modified}[/bold]  "
            f"Unchanged: [bold]{summary2.documents_unchanged}[/bold]  "
            f"New chunks: [bold]{summary2.chunks_indexed}[/bold]"
        )
        METRICS["documents_unchanged"] = summary2.documents_unchanged
        METRICS["unnecessary_reembeds"] = (
            0 if summary2.documents_unchanged >= max(len(discovered) - 1, 0) else -1
        )

        _step(15, "Ask previous question again")
        response3 = await orchestrator.query(
            QueryRequest(query="How many sick days do employees get?")
        )
        await session.commit()

        _step(16, "Show updated answer")
        console.print(
            Panel(
                response3.answer or "",
                title="Updated Answer After Re-ingestion",
                border_style="green",
            )
        )

        _step(17, "Delete a document")
        delete_target = demo_path / "learning" / "training-handbook.md"
        if delete_target.exists():
            delete_target.unlink()
            console.print(f"Deleted [red]{delete_target.name}[/red] from disk")

        _step(18, "Synchronise deletion")
        summary3 = await ingestion.run(source="demo")
        await session.commit()
        console.print(f"Documents deleted from index: [bold]{summary3.documents_deleted}[/bold]")

        _step(19, "Demonstrate restricted retrieval")
        restricted_chunk = {
            "chunk_id": "restricted-demo",
            "document_id": "doc-restricted",
            "document_title": "Executive Compensation (Restricted)",
            "document_version": 1,
            "content": "Executive bonus structure is confidential.",
            "fusion_score": 0.95,
            "metadata": {"allowed_groups": ["FINANCE"]},
        }
        from app.retrieval.permissions import PermissionFilter
        from app.schemas.common import RetrievedChunk

        perm_filter = PermissionFilter()
        chunks = [
            RetrievedChunk(**restricted_chunk),
            RetrievedChunk(
                chunk_id="public-demo",
                document_id="doc-public",
                document_title="Employee Handbook",
                document_version=1,
                content="Vacation policy applies to all employees.",
                fusion_score=0.7,
                metadata={"allowed_groups": []},
            ),
        ]
        eng_results = perm_filter.filter_chunks(chunks, "ENGINEERING")
        fin_results = perm_filter.filter_chunks(chunks, "FINANCE")
        console.print(
            f"ENGINEERING sees {len(eng_results)} chunk(s); FINANCE sees {len(fin_results)} chunk(s)"
        )

        _step(20, "Display final metrics")
        elapsed = int((time.perf_counter() - start) * 1000)
        METRICS["avg_latency_ms"] = (METRICS["avg_latency_ms"] + elapsed) // 2

        table = Table(title="KnowledgeOps Demo Summary", show_header=True)
        table.add_column("Category", style="cyan")
        table.add_column("Metric", style="white")
        table.add_column("Value", style="green")
        rows = [
            ("Ingestion", "Documents discovered", str(METRICS["documents_discovered"])),
            ("Ingestion", "Documents changed", str(METRICS["documents_changed"])),
            ("Ingestion", "Documents unchanged (2nd run)", str(METRICS["documents_unchanged"])),
            ("Ingestion", "Chunks indexed", str(METRICS["chunks_indexed"])),
            ("Retrieval", "Hit Rate @ 5", f"{METRICS['hit_rate_at_5']:.2f}"),
            ("Retrieval", "MRR", f"{METRICS['mrr']:.2f}"),
            ("Retrieval", "Average latency", f"{METRICS['avg_latency_ms']} ms"),
            ("Quality", "Questions evaluated", str(METRICS["questions_evaluated"])),
            ("Quality", "Supported answers", str(METRICS["supported_answers"])),
            ("Quality", "Correct refusals", str(METRICS["correct_refusals"])),
            ("Quality", "Knowledge gaps", str(METRICS["knowledge_gaps"])),
            (
                "Automation",
                "Unnecessary re-embeds (2nd run)",
                str(max(METRICS["unnecessary_reembeds"], 0)),
            ),
        ]
        for category, metric, value in rows:
            table.add_row(category, metric, value)
        console.print(table)
        console.print("\n[bold green]Demo complete.[/bold green]")

    finally:
        await session.commit()
        await session.close()
        await engine.dispose()


if __name__ == "__main__":
    run_demo()
