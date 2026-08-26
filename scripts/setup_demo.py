"""Initialize a clean demo knowledge base and optional index reset."""

from __future__ import annotations

import shutil
from pathlib import Path

from rich.console import Console

from app.core.config import get_settings

console = Console()

DEMO_FILES: dict[str, str] = {
    "hr/employee-handbook.md": """# Employee Handbook

## Vacation Policy
All full-time employees receive 20 days of paid vacation per year. Vacation requests must be submitted at least two weeks in advance through the HR portal.

## Remote Work
Employees may work remotely up to three days per week with manager approval. Core collaboration hours are 10:00-15:00 local time.

## Benefits
Health insurance, dental, and vision coverage begin on the first day of employment.
""",
    "hr/leave-policy.md": """# Leave Policy

## Sick Leave
Employees accrue 10 sick days annually. Unused sick days do not roll over.

## Parental Leave
Primary caregivers receive 12 weeks of paid parental leave. Secondary caregivers receive 4 weeks.
""",
    "it/vpn-guide.md": """# VPN Guide

## Connecting to VPN
Install the corporate VPN client and authenticate with your SSO credentials. Use gateway vpn.corp.example.com.

## Password Reset
To reset your password, visit the IT self-service portal or contact the help desk at extension 4357.
""",
    "it/equipment-policy.md": """# IT Equipment Policy

## Laptop Standards
Engineering staff receive MacBook Pro or equivalent Windows laptops. Replacement cycle is 3 years.

## Software Installation
Only approved software from the company catalog may be installed on corporate devices.
""",
    "security/information-security-policy.md": """# Information Security Policy

## Data Classification
All company data is classified as Public, Internal, Confidential, or Restricted.

## Incident Response
Report security incidents within one hour to security@corp.example.com or the SOC hotline.
""",
    "finance/travel-expense-policy.md": """# Travel Expense Policy

## Approval Thresholds
Expenses under $500 require manager approval. Expenses over $500 require director approval.

## Reimbursement
Submit expense reports within 30 days of travel completion via the finance portal.
""",
    "operations/business-continuity.md": """# Business Continuity Plan

## Emergency Procedures
In case of office closure, employees should follow remote work procedures and check the status page.

## Office Access
Badge access is required 24/7. Visitors must be escorted at all times.
""",
    "procurement/supplier-onboarding.md": """# Supplier Onboarding

## Required Documents
New suppliers must provide W-9, insurance certificate, and signed MSA before engagement.

## Approval Matrix
Purchases under $10,000 require procurement manager approval.
""",
    "engineering/deployment-guide.md": """# Deployment Guide

## CI/CD Pipeline
All deployments go through staging, automated tests, and manual approval before production.

## Rollback
Use the deployment dashboard to roll back to the previous stable release within 5 minutes.
""",
    "engineering/code-review-standards.md": """# Code Review Standards

## Requirements
All pull requests require at least one approval from a senior engineer. Tests must pass before merge.

## Security Review
Changes touching authentication or PII require security team review.
""",
    "learning/onboarding-checklist.md": """# Onboarding Checklist

## Week One
Complete HR orientation, IT setup, security training, and meet your buddy.

## Week Two
Review team documentation and complete role-specific training modules.
""",
    "learning/training-handbook.md": """# Training Handbook

## Annual Requirements
All employees must complete security awareness and compliance training annually.

## Professional Development
Each employee has a $1,500 annual learning budget for courses and conferences.
""",
}


def _write_demo_documents(demo_path: Path) -> int:
    """Write synthetic demo documents if the folder is empty or reset."""
    count = 0
    for relative_path, content in DEMO_FILES.items():
        file_path = demo_path / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        count += 1
    return count


def setup_demo(*, reset_index: bool = False, reset_documents: bool = False) -> Path:
    """
    Prepare demo_knowledge folder with synthetic business documents.

    Args:
        reset_index: If True, remove local SQLite test artifacts (when used in tests).
        reset_documents: If True, wipe and recreate demo_knowledge contents.
    """
    settings = get_settings()
    demo_path = Path(settings.demo_knowledge_path)
    if not demo_path.is_absolute():
        demo_path = settings.project_root / demo_path

    if reset_documents and demo_path.exists():
        shutil.rmtree(demo_path)
    demo_path.mkdir(parents=True, exist_ok=True)

    existing = list(demo_path.rglob("*.*"))
    if len(existing) < 10:
        count = _write_demo_documents(demo_path)
        console.print(f"[green]Created {count} demo documents in {demo_path}[/green]")
    else:
        console.print(f"[blue]Using existing {len(existing)} files in {demo_path}[/blue]")

    if reset_index:
        results_dir = settings.project_root / "evals" / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        console.print("[dim]Demo knowledge base ready for ingestion.[/dim]")

    return demo_path


if __name__ == "__main__":
    import typer

    cli = typer.Typer()

    @cli.command()
    def main(
        reset: bool = typer.Option(False, "--reset", help="Reset demo documents"),
    ) -> None:
        setup_demo(reset_index=True, reset_documents=reset)

    cli()
