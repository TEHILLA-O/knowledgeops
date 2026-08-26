"""Demo knowledge folder discovery source."""

from __future__ import annotations

from pathlib import Path

from app.core.config import Settings, get_settings
from app.ingestion.discovery.local_folder import LocalFolderSource


class DemoSource(LocalFolderSource):
    """Discover documents from the configured demo_knowledge folder."""

    def __init__(self, settings: Settings | None = None) -> None:
        settings = settings or get_settings()
        sources_config = settings.ingestion_config.get("sources", {}).get("demo", {})
        demo_path = sources_config.get("path", settings.demo_knowledge_path)
        super().__init__(
            folder_path=Path(demo_path),
            source_name="demo",
            settings=settings,
        )
