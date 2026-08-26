"""Evaluation dataset loading."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import Settings, get_settings
from app.core.exceptions import NotFoundError, ValidationError


@dataclass
class EvalQuestion:
    question: str
    expected_documents: list[str]
    metadata: dict[str, Any]


@dataclass
class EvalDataset:
    name: str
    description: str
    questions: list[EvalQuestion]
    k_values: list[int]


def _datasets_dir(settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    path = settings.project_root / "evals" / "datasets"
    path.mkdir(parents=True, exist_ok=True)
    return path


def list_datasets(settings: Settings | None = None) -> list[str]:
    """List available dataset names."""
    directory = _datasets_dir(settings)
    names: list[str] = []
    for path in sorted(directory.glob("*.json")):
        names.append(path.stem)
    for path in sorted(directory.glob("*.yaml")):
        names.append(path.stem)
    for path in sorted(directory.glob("*.yml")):
        names.append(path.stem)
    return sorted(set(names))


def load_dataset(name: str, settings: Settings | None = None) -> EvalDataset:
    """Load evaluation dataset by name from evals/datasets/."""
    directory = _datasets_dir(settings)
    for ext in (".json", ".yaml", ".yml"):
        path = directory / f"{name}{ext}"
        if path.exists():
            return _parse_dataset_file(path, name)
    raise NotFoundError(f"Evaluation dataset '{name}' not found in {directory}")


def _parse_dataset_file(path: Path, name: str) -> EvalDataset:
    raw_text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        data = json.loads(raw_text)
    else:
        import yaml

        data = yaml.safe_load(raw_text) or {}

    if not isinstance(data, dict):
        raise ValidationError(f"Dataset {name} must be a JSON/YAML object")

    questions_raw = data.get("questions", [])
    if not questions_raw:
        raise ValidationError(f"Dataset {name} has no questions")

    questions: list[EvalQuestion] = []
    for item in questions_raw:
        if not isinstance(item, dict) or "question" not in item:
            raise ValidationError(f"Invalid question entry in dataset {name}")
        expected = item.get("expected_documents") or item.get("expected_document")
        if isinstance(expected, str):
            expected_docs = [expected]
        elif isinstance(expected, list):
            expected_docs = [str(d) for d in expected]
        else:
            expected_docs = []
        questions.append(
            EvalQuestion(
                question=str(item["question"]),
                expected_documents=expected_docs,
                metadata=dict(item.get("metadata", {})),
            )
        )

    return EvalDataset(
        name=data.get("name", name),
        description=str(data.get("description", "")),
        questions=questions,
        k_values=[int(k) for k in data.get("k_values", [1, 3, 5, 10])],
    )


def ensure_default_dataset(settings: Settings | None = None) -> None:
    """Create a sample dataset if none exists."""
    directory = _datasets_dir(settings)
    sample = directory / "sample.json"
    if sample.exists():
        return
    sample.write_text(
        json.dumps(
            {
                "name": "sample",
                "description": "Sample evaluation dataset",
                "k_values": [1, 3, 5],
                "questions": [
                    {
                        "question": "What is the vacation policy?",
                        "expected_documents": ["hr-handbook"],
                    },
                    {
                        "question": "How do I reset my password?",
                        "expected_documents": ["it-support-guide"],
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
