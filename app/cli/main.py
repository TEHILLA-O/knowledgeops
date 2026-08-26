"""KnowledgeOps Typer CLI with Rich output."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import typer
import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings, get_settings
from app.core.logging import setup_logging

app = typer.Typer(
    name="knowledgeops",
    help="KnowledgeOps RAG Automation Platform CLI",
    no_args_is_help=True,
)
console = Console()


def _run_async(coro: Any) -> Any:
    return asyncio.run(coro)


async def _build_session_context(
    settings: Settings | None = None,
) -> tuple[AsyncSession, Any, Any, Settings, AsyncEngine]:
    """Create DB session, Qdrant, and embedding provider for CLI commands."""
    from app.db.models import Base
    from app.providers.factory import create_embedding_provider
    from app.retrieval.qdrant_client import QdrantService

    settings = settings or get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session = session_factory()
    qdrant = QdrantService(settings)
    embedding = create_embedding_provider(settings)
    await qdrant.ensure_collection(embedding.vector_size)
    return session, qdrant, embedding, settings, engine


async def _close_session(session: AsyncSession, engine: AsyncEngine) -> None:
    await session.commit()
    await session.close()
    await engine.dispose()


@app.command("demo")
def demo(
    skip_setup: bool = typer.Option(False, "--skip-setup", help="Skip knowledge base reset"),
) -> None:
    """Run the full 20-step case study demonstration."""
    setup_logging()
    if not skip_setup:
        from scripts.setup_demo import setup_demo

        setup_demo(reset_index=True)
    from scripts.run_case_study_demo import run_demo

    run_demo()


@app.command("ingest")
def ingest(
    source: str = typer.Option("demo", "--source", "-s", help="Document source name"),
) -> None:
    """Run document ingestion for a source."""
    setup_logging()

    async def _ingest() -> None:
        from app.api.deps import IngestionService

        session, qdrant, _, settings, engine = await _build_session_context()
        try:
            service = IngestionService(session, qdrant, settings)
            with console.status(f"[bold green]Ingesting from source '{source}'..."):
                summary = await service.run(source=source)
            table = Table(title="Ingestion Summary")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            for key, value in summary.model_dump().items():
                table.add_row(str(key), str(value))
            console.print(table)
        finally:
            await _close_session(session, engine)

    _run_async(_ingest())


@app.command("query")
def query(
    text: str = typer.Argument(..., help="Question to ask"),
    user_group: str | None = typer.Option(None, "--user-group", "-g"),
    debug: bool = typer.Option(False, "--debug", help="Include retrieval debug info"),
) -> None:
    """Ask a grounded question against the knowledge base."""
    setup_logging()

    async def _query() -> None:
        from app.api.deps import QueryOrchestrator, Repositories
        from app.generation.service import QueryService as GenerationQueryService
        from app.knowledge_gaps.service import KnowledgeGapService
        from app.retrieval.service import RetrievalService
        from app.schemas.common import QueryRequest

        session, qdrant, _, settings, engine = await _build_session_context()
        try:
            repos = Repositories(session)
            retrieval = RetrievalService(qdrant=qdrant, settings=settings)
            generation = GenerationQueryService(retrieval_service=retrieval, settings=settings)
            gap_service = KnowledgeGapService(repos.knowledge_gaps, settings)
            orchestrator = QueryOrchestrator(repos, generation, retrieval, gap_service)

            request = QueryRequest(query=text, user_group=user_group, include_debug=debug)
            with console.status("[bold green]Searching and generating answer..."):
                response = await orchestrator.query(request)

            console.print(
                Panel(
                    response.answer or "[dim]No answer[/dim]", title="Answer", border_style="green"
                )
            )
            if response.confidence:
                console.print(
                    f"[bold]Confidence:[/bold] {response.confidence.level.value} "
                    f"({response.confidence.score:.2f})"
                )
            if response.citations:
                console.print("\n[bold]Citations:[/bold]")
                for idx, citation in enumerate(response.citations, start=1):
                    console.print(f"  [{idx}] {citation.document_title} (v{citation.version})")
            if debug and response.debug:
                console.print("\n[bold]Debug:[/bold]")
                console.print_json(data=response.debug)
        finally:
            await _close_session(session, engine)

    _run_async(_query())


@app.command("search")
def search_cmd(
    text: str = typer.Argument(..., help="Search query"),
    top_k: int = typer.Option(5, "--top-k", "-k"),
    user_group: str | None = typer.Option(None, "--user-group", "-g"),
) -> None:
    """Search the knowledge base without generation."""
    setup_logging()

    async def _search() -> None:
        from app.retrieval.service import RetrievalService
        from app.schemas.common import SearchRequest

        session, qdrant, _, settings, engine = await _build_session_context()
        try:
            retrieval = RetrievalService(qdrant=qdrant, settings=settings)
            request = SearchRequest(query=text, top_k=top_k, user_group=user_group)
            with console.status("[bold green]Searching..."):
                chunks, debug = await retrieval.search(
                    request.query,
                    user_group=request.user_group,
                    top_k=request.top_k,
                )
            table = Table(
                title=f"Search Results ({len(chunks)} hits, {debug.get('latency_ms', 0)} ms)"
            )
            table.add_column("#", style="dim")
            table.add_column("Document", style="cyan")
            table.add_column("Score", style="green")
            table.add_column("Snippet")
            for idx, chunk in enumerate(chunks, start=1):
                score = chunk.rerank_score or chunk.fusion_score or chunk.dense_score or 0.0
                snippet = chunk.content[:120].replace("\n", " ") + (
                    "..." if len(chunk.content) > 120 else ""
                )
                table.add_row(str(idx), chunk.document_title, f"{score:.3f}", snippet)
            console.print(table)
        finally:
            await _close_session(session, engine)

    _run_async(_search())


@app.command("documents")
def documents(
    page: int = typer.Option(1, "--page", "-p"),
    page_size: int = typer.Option(20, "--page-size"),
    source: str | None = typer.Option(None, "--source"),
    search: str | None = typer.Option(None, "--search"),
) -> None:
    """List indexed documents."""
    setup_logging()

    async def _documents() -> None:
        from app.repositories.document_repo import DocumentRepository

        session, _, _, _, engine = await _build_session_context()
        try:
            repo = DocumentRepository(session)
            items, total = await repo.list_documents(
                page=page,
                page_size=page_size,
                source=source,
                search=search,
            )
            table = Table(title=f"Documents (page {page}, total {total})")
            table.add_column("Title", style="cyan")
            table.add_column("Source")
            table.add_column("Version")
            table.add_column("Status")
            table.add_column("Chunks")
            for doc in items:
                table.add_row(
                    doc.title[:50],
                    doc.source,
                    str(doc.current_version),
                    doc.status,
                    str(doc.chunk_count),
                )
            console.print(table)
        finally:
            await _close_session(session, engine)

    _run_async(_documents())


@app.command("gaps")
def gaps(
    page: int = typer.Option(1, "--page", "-p"),
    page_size: int = typer.Option(20, "--page-size"),
    status: str | None = typer.Option(None, "--status"),
) -> None:
    """List detected knowledge gaps."""
    setup_logging()

    async def _gaps() -> None:
        from app.repositories.knowledge_gap_repo import KnowledgeGapRepository

        session, _, _, _, engine = await _build_session_context()
        try:
            repo = KnowledgeGapRepository(session)
            items, total = await repo.list_gaps(page=page, page_size=page_size, status=status)
            table = Table(title=f"Knowledge Gaps (total {total})")
            table.add_column("Question", style="cyan")
            table.add_column("Frequency")
            table.add_column("Topic")
            table.add_column("Status")
            for gap in items:
                table.add_row(
                    gap.question[:60],
                    str(gap.frequency),
                    (gap.suggested_topic or "")[:30],
                    gap.status,
                )
            console.print(table)
        finally:
            await _close_session(session, engine)

    _run_async(_gaps())


@app.command("evaluate")
def evaluate(
    dataset: str = typer.Option("sample", "--dataset", "-d"),
    top_k: int = typer.Option(10, "--top-k", "-k"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Save results JSON"),
) -> None:
    """Run retrieval evaluation against a dataset."""
    setup_logging()
    from scripts.run_evaluation import run_evaluation as run_eval_script

    result = _run_async(run_eval_script(dataset_name=dataset, top_k=top_k, output_path=output))
    if result:
        console.print(
            Panel(json.dumps(result.get("metrics", {}), indent=2), title="Evaluation Metrics")
        )


@app.command("benchmark")
def benchmark(
    iterations: int = typer.Option(3, "--iterations", "-n"),
    output: Path | None = typer.Option(None, "--output", "-o"),
) -> None:
    """Benchmark ingestion, embedding, retrieval, and query latency."""
    setup_logging()
    from scripts.benchmark_rag import run_benchmark

    results = _run_async(run_benchmark(iterations=iterations))
    console.print(Panel(json.dumps(results, indent=2), title="Benchmark Results"))
    if output:
        output.write_text(json.dumps(results, indent=2), encoding="utf-8")
        console.print(f"[green]Saved benchmark to {output}[/green]")


@app.command("status")
def status() -> None:
    """Show platform health and index statistics."""
    setup_logging()

    async def _status() -> None:
        from sqlalchemy import func, select, text

        from app.db.models import Chunk, Document, KnowledgeGap, QueryRecord
        from app.repositories.analytics_repo import AnalyticsRepository

        session, qdrant, _, settings, engine = await _build_session_context()
        try:
            postgres_ok = False
            try:
                await session.execute(text("SELECT 1"))
                postgres_ok = True
            except Exception:
                postgres_ok = False

            qdrant_ok = await qdrant.health_check()
            try:
                point_count = await qdrant.count_points()
            except Exception:
                point_count = 0

            doc_count = (
                await session.execute(
                    select(func.count()).select_from(Document).where(Document.is_deleted.is_(False))
                )
            ).scalar_one()
            chunk_count = (
                await session.execute(
                    select(func.count()).select_from(Chunk).where(Chunk.is_active.is_(True))
                )
            ).scalar_one()
            gap_count = (
                await session.execute(select(func.count()).select_from(KnowledgeGap))
            ).scalar_one()
            query_count = (
                await session.execute(select(func.count()).select_from(QueryRecord))
            ).scalar_one()

            analytics = AnalyticsRepository(session)
            summary = await analytics.get_summary()

            table = Table(title="KnowledgeOps Status")
            table.add_column("Component", style="cyan")
            table.add_column("Status", style="green")
            table.add_row("PostgreSQL", "[green]up[/green]" if postgres_ok else "[red]down[/red]")
            table.add_row("Qdrant", "[green]up[/green]" if qdrant_ok else "[red]down[/red]")
            table.add_row("Documents", str(doc_count))
            table.add_row("Active Chunks (DB)", str(chunk_count))
            table.add_row("Qdrant Points", str(point_count))
            table.add_row("Queries", str(query_count))
            table.add_row("Knowledge Gaps", str(gap_count))
            table.add_row("Index Health", summary.index_health or "unknown")
            table.add_row("Embedding Provider", settings.embedding_provider)
            table.add_row("Generation Provider", settings.generation_provider)
            console.print(table)
        finally:
            await _close_session(session, engine)

    _run_async(_status())


@app.command("api")
def api(
    host: str = typer.Option("0.0.0.0", "--host"),
    port: int = typer.Option(8000, "--port", "-p"),
    reload: bool = typer.Option(False, "--reload"),
) -> None:
    """Start the FastAPI server."""
    setup_logging(get_settings().log_level)
    console.print(
        Panel(
            f"Starting API at http://{host}:{port}\nDocs: http://{host}:{port}/docs",
            title="KnowledgeOps API",
            border_style="blue",
        )
    )
    uvicorn.run("app.main:app", host=host, port=port, reload=reload)


@app.command("migrate")
def migrate(
    revision: str = typer.Option("head", "--revision", "-r"),
) -> None:
    """Run Alembic database migrations."""
    project_root = get_settings().project_root
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", revision],
        cwd=project_root,
        check=False,
    )
    if result.returncode != 0:
        raise typer.Exit(code=result.returncode)
    console.print("[green]Migrations applied successfully.[/green]")


if __name__ == "__main__":
    app()
