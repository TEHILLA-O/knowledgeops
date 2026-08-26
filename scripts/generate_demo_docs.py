#!/usr/bin/env python3
"""Regenerate Acme Corp demo knowledge base and evaluation datasets."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_ROOT = PROJECT_ROOT / "demo_knowledge"
EVALS_DIR = PROJECT_ROOT / "evals" / "datasets"

COMPANY = "Acme Corp"
POLICY_PREFIX = "ACM-POL"


def word_count(text: str) -> int:
    return len(text.split())


def expand_paragraphs(paragraphs: list[str], target_words: int = 900) -> str:
    """Repeat and vary paragraphs until target word count is reached."""
    body: list[str] = []
    total = 0
    idx = 0
    while total < target_words:
        para = paragraphs[idx % len(paragraphs)]
        body.append(para)
        total += word_count(para)
        idx += 1
    return "\n\n".join(body)


def frontmatter(
    *,
    department: str,
    policy_id: str,
    visibility: str = "PUBLIC_INTERNAL",
    allowed_groups: list[str] | None = None,
    version: str = "1.0",
) -> str:
    groups = allowed_groups or []
    groups_yaml = json.dumps(groups)
    return (
        textwrap.dedent(
            f"""\
        ---
        company: {COMPANY}
        department: {department}
        policy_id: {policy_id}
        visibility: {visibility}
        allowed_groups: {groups_yaml}
        version: {version}
        synthetic: true
        ---

        <!-- SYNTHETIC DOCUMENT FOR KNOWLEDGEOPS DEMO ONLY -->
        <!-- visibility: {visibility} | allowed_groups: {groups_yaml} -->
        """
        ).strip()
        + "\n\n"
    )


def write_doc(rel_path: str, content: str) -> None:
    path = DEMO_ROOT / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def hr_docs() -> list[str]:
    created: list[str] = []

    handbook_body = textwrap.dedent(
        f"""\
        # {COMPANY} Employee Handbook

        **Document ID:** {POLICY_PREFIX}-HR-001 | **Effective:** 2024-01-01 | **Owner:** People Operations

        ## Welcome to Acme Corp

        This handbook describes employment practices for all Acme Corp team members worldwide.
        Acme Corp is a fictional enterprise software company headquartered in Austin, Texas,
        with regional offices in Dublin, Singapore, and Toronto. Nothing in this document
        constitutes a contract of employment.

        ## Employment Categories

        Acme classifies workers as full-time employees, part-time employees, fixed-term
        contractors, and interns. Full-time employees work a standard 40-hour week unless
        local law requires otherwise. Managers must record category changes in Workday within
        five business days.

        ## Code of Conduct

        Employees must act with integrity, respect colleagues, and protect company assets.
        Harassment, discrimination, retaliation, and dishonesty are prohibited. Report concerns
        to your manager, HR Business Partner, or the Ethics Hotline (1-800-ACME-ETH).

        ## Working Hours and Attendance

        Core collaboration hours are 10:00–16:00 in the employee's local time zone.
        Flexible scheduling is permitted with manager approval. Chronic absenteeism without
        approved leave may result in disciplinary action.

        ## Compensation Philosophy

        Acme targets the 50th percentile of market total cash compensation by role and
        geography. Annual merit cycles occur in March. Bonus eligibility is described in
        department-specific compensation guides.

        ## Benefits Overview

        U.S. employees receive medical, dental, vision, life, and disability coverage.
        International packages follow local statutory requirements. The 401(k) plan includes
        a 4% company match after 90 days of service.

        ## Leave and Time Off

        Refer to the Leave Policy ({POLICY_PREFIX}-HR-003) for vacation accrual, sick leave,
        and carry-forward rules. Public holidays follow the official Acme holiday calendar
        published each November.

        ## Remote and Hybrid Work

        See the Remote Working Policy ({POLICY_PREFIX}-HR-002). Employees must maintain
        a professional workspace and comply with information security requirements.

        ## Performance Management

        Acme uses quarterly check-ins and an annual performance review. Ratings inform
        compensation, promotion, and development planning. Calibration sessions ensure
        consistency across teams.

        ## Learning and Development

        Each employee receives an annual learning stipend of USD 1,500. Mandatory compliance
        training must be completed within 30 days of hire and annually thereafter.

        ## Separation of Employment

        Voluntary resignations require two weeks' notice for non-exempt roles and four weeks
        for director-level and above. Exit interviews are encouraged. Company property must
        be returned on the last working day.

        ## Questions

        Contact peopleops@acme-corp.example for handbook clarifications.
        """
    )
    handbook = (
        frontmatter(department="hr", policy_id=f"{POLICY_PREFIX}-HR-001")
        + handbook_body
        + "\n\n"
        + expand_paragraphs(
            [
                "Acme promotes a culture of psychological safety where employees can raise concerns "
                "without fear of retaliation. Speak-up channels include managers, HRBPs, and anonymous ethics reporting.",
                "Workplace accommodations for disabilities or religious practices are available upon request. "
                "Submit ADA accommodation forms to accommodations@acme-corp.example.",
                "Employee referrals are encouraged through the Talent Referral Program (TRP). Successful hires "
                "may qualify for referral bonuses per the active TRP schedule.",
            ],
            200,
        )
    )
    write_doc("hr/employee-handbook.md", handbook)
    created.append("hr/employee-handbook.md")

    remote = frontmatter(department="hr", policy_id=f"{POLICY_PREFIX}-HR-002") + expand_paragraphs(
        [
            "Acme Corp supports hybrid and remote work arrangements where business needs allow. "
            "Employees may work remotely up to three days per week with manager approval.",
            "Remote employees must use company-approved VPN (ACM-VPN-STD) when accessing internal systems. "
            "Home networks should use WPA3 encryption where supported.",
            "International remote work beyond 30 days requires written approval from HR and Tax. "
            "Unauthorized work from restricted jurisdictions may violate export controls.",
            "Equipment for remote work is provisioned according to IT Policy ACM-IT-001. "
            "Employees are responsible for securing laptops and preventing unauthorized access.",
            "Core meetings should be scheduled within documented collaboration hours. "
            "Managers must ensure equitable participation for distributed team members.",
        ],
        850,
    )
    remote = (
        frontmatter(department="hr", policy_id=f"{POLICY_PREFIX}-HR-002")
        + "# Acme Corp Remote Working Policy\n\n"
        + remote
    )
    write_doc("hr/remote-working-policy.md", remote)
    created.append("hr/remote-working-policy.md")

    leave_core = textwrap.dedent(
        f"""\
        # Acme Corp Leave Policy

        **Policy Number:** {POLICY_PREFIX}-HR-003 | **Version:** 1.0 | **Effective:** 2024-01-01

        ## Purpose

        This policy defines how Acme Corp employees accrue, request, and use paid time off (PTO),
        including annual leave, sick leave, and special leave categories.

        ## Annual Leave Accrual

        Full-time employees accrue 20 days of annual leave per calendar year, pro-rated for
        partial years. Accrual begins on the first day of employment. Part-time employees accrue
        on a pro-rata basis using their scheduled hours.

        ## Carry Forward Rules

        **Employees may carry forward up to 5 days of unused annual leave** into the next
        calendar year. Any balance exceeding five days is forfeited on January 1 unless a written
        exception is approved by the CHRO for business-critical roles. Carried days must be used
        by March 31 of the following year or they expire.

        ## Requesting Leave

        Submit requests in Workday at least five business days in advance for planned vacation.
        Manager approval is required. Teams should maintain minimum coverage of 70% during peak
        release windows (November–December and May–June).

        ## Sick Leave

        Employees receive 10 days of paid sick leave annually. Sick leave does not carry forward.
        For absences longer than three consecutive days, a medical certificate may be requested.

        ## Parental Leave

        Primary caregivers receive 16 weeks of paid parental leave. Secondary caregivers receive
        6 weeks. Leave must commence within 12 months of birth, adoption, or surrogacy.

        ## Bereavement Leave

        Up to 5 days paid leave for immediate family. Up to 2 days for extended family.
        Additional unpaid leave may be granted at manager discretion.

        ## Public Holidays

        Acme observes 10 U.S. federal holidays for U.S. employees. International employees
        follow local statutory holiday schedules published by Regional HR.

        ## Leave Without Pay

        Unpaid leave requires director approval and HR documentation. Benefits may be suspended
        during extended unpaid leave per plan rules.

        ## Record Keeping

        HR maintains leave balances in Workday. Employees should verify balances quarterly and
        report discrepancies within 30 days.

        ## Policy Governance

        Questions: leave-admin@acme-corp.example. Changes require CHRO approval and union
        consultation where applicable.
        """
    )
    leave_policy = (
        frontmatter(department="hr", policy_id=f"{POLICY_PREFIX}-HR-003", version="1.0")
        + leave_core
        + "\n\n"
        + expand_paragraphs(
            [
                "Blackout periods may apply for finance close weeks. Managers will communicate team-specific "
                "blackouts at least 60 days in advance.",
                "Employees transferring between countries should consult Global Mobility for leave balance "
                "conversion rules before relocation.",
                "Unused sabbatical eligibility accrues after seven years of continuous service per the "
                "Sabbatical Addendum ACM-HR-SAB-01.",
            ],
            250,
        )
    )
    write_doc("hr/leave-policy.md", leave_policy)
    created.append("hr/leave-policy.md")

    leave_v2_core = textwrap.dedent(
        f"""\
        # Acme Corp Leave Policy — Version 2.0 Reference Content

        **Policy Number:** {POLICY_PREFIX}-HR-003 | **Version:** 2.0 (DRAFT FOR DEMO UPDATE)

        ## Carry Forward Rules (Updated)

        **Employees may carry forward up to 8 days of unused annual leave** into the next
        calendar year. Any balance exceeding eight days is forfeited on January 1 unless a
        written exception is approved by the CHRO. Carried days must be used by April 30 of
        the following year.

        All other sections remain identical to version 1.0. This file is used by the demo
        script to simulate a policy version change affecting RAG answers.
        """
    )
    leave_v2 = (
        frontmatter(department="hr", policy_id=f"{POLICY_PREFIX}-HR-003", version="2.0")
        + leave_v2_core
        + "\n\n"
        + expand_paragraphs(
            [
                "Version 2.0 was approved by the CHRO on 2025-06-01 following employee feedback survey ACM-SURV-2025-LEAVE.",
                "HR will communicate the updated carry-forward limit via email and Slack #people-updates.",
                "Workday accrual rules will be updated automatically on the effective date of the policy rollout.",
            ],
            450,
        )
    )
    write_doc("hr/leave-policy-v2-content.md", leave_v2)
    created.append("hr/leave-policy-v2-content.md")

    comp = frontmatter(
        department="hr",
        policy_id=f"{POLICY_PREFIX}-HR-004",
        visibility="RESTRICTED",
        allowed_groups=["HR"],
    ) + expand_paragraphs(
        [
            "# Acme Corp Compensation & Benefits Guide (HR Confidential)\n\n"
            "This RESTRICTED document is for HR Business Partners only. Do not distribute to employees.",
            "Salary bands are identified by codes such as ACM-BAND-E4 for Senior Engineer and ACM-BAND-M2 "
            "for Engineering Manager. Midpoint targets are reviewed each April.",
            "Equity grants follow the ACM-EQ-POOL-2024 plan. New hires at level E5+ may receive "
            "25,000–60,000 RSUs vesting over four years with a one-year cliff.",
            "Spot bonuses require VP approval above USD 5,000. Documentation must be stored in the "
            "Compensation Vault with ticket COMP-REQ-####.",
            "Benefits enrollment changes outside open enrollment need Qualifying Life Event documentation "
            "within 30 days.",
        ],
        700,
    )
    write_doc("hr/compensation-benefits.md", comp)
    created.append("hr/compensation-benefits.md")

    perf = frontmatter(
        department="hr",
        policy_id=f"{POLICY_PREFIX}-HR-005",
        visibility="RESTRICTED",
        allowed_groups=["HR"],
    ) + expand_paragraphs(
        [
            "# Performance Review Administration Guide (RESTRICTED)\n\n"
            'visibility: RESTRICTED | allowed_groups: ["HR"]',
            "Calibration sessions use rating scale ACM-PERF-5: Exceptional, Exceeds, Meets, Developing, Unsatisfactory.",
            "Forced distribution targets: 10% Exceptional, 25% Exceeds, 55% Meets, 8% Developing, 2% Unsatisfactory.",
            "PIP templates are stored under HR-CONF-PIP-2024. Managers may not share PIP details with peers.",
            "Promotion packets require two leadership references and a skills matrix score of 4.0 or higher.",
        ],
        650,
    )
    write_doc("hr/performance-review-guide.md", perf)
    created.append("hr/performance-review-guide.md")

    return created


def department_docs(
    dept: str,
    docs: list[tuple[str, str, str, int]],
) -> list[str]:
    """Write docs as (filename, title, policy_id, target_words)."""
    created: list[str] = []
    for filename, title, policy_id, target in docs:
        body = expand_paragraphs(
            [
                f"{title} applies to all {COMPANY} personnel in the {dept} domain. "
                f"Policy reference {policy_id} supersedes prior informal guidance.",
                f"Compliance with {policy_id} is audited quarterly. Non-compliance must be reported "
                "via the Acme Governance Portal within 24 hours of discovery.",
                f"Roles and responsibilities are defined using RACI matrices maintained by the "
                f"{dept.title()} leadership team. Escalation path: Manager → Director → VP.",
                "Exceptions require documented risk acceptance signed by the department VP and "
                "stored for seven years per records retention schedule ACM-REC-001.",
                f"Training on this policy is mandatory within 30 days of hire. Course code "
                f"ACM-LRN-{dept.upper()[:3]}-101 must appear on the employee learning transcript.",
            ],
            target,
        )
        content = (
            frontmatter(department=dept, policy_id=policy_id)
            + f"# {title}\n\n**Policy ID:** {policy_id}\n\n"
            + body
        )
        rel = f"{dept}/{filename}"
        write_doc(rel, content)
        created.append(rel)
    return created


def engineering_contractor_policy() -> str:
    core = textwrap.dedent(
        f"""\
        # Contractor Equipment Policy

        **Policy ID:** {POLICY_PREFIX}-ENG-003 | **Audience:** Engineering | **Visibility:** ENGINEERING

        ## Scope

        This policy governs laptop and peripheral provisioning for engineering contractors
        engaged through approved vendors. Full-time employees should refer to ACM-IT-001.

        ## Eligibility

        Contractors with engagements of 90+ days may request a standard engineering laptop
        (SKU ACM-LTP-ENG-14). Shorter engagements use BYOD with mandatory MDM enrollment.

        ## Approved Hardware SKUs

        - Laptop: ACM-LTP-ENG-14 (14" developer spec, 32GB RAM)
        - Monitor: ACM-MON-27-4K (up to two units)
        - Dock: ACM-DOCK-USB4
        - Headset: ACM-AUD-ANC-01

        ## Software

        Contractors receive licenses for IDE-PRO-ACM, GitEnterprise, and VPN-ENG tier.
        Admin/root access requires ticket ENG-ROOT-REQ and security approval.

        ## Return Process

        Equipment must be returned within five business days of contract end. Shipping labels
        are generated via IT-RETURN portal. Lost equipment may be billed to the vendor per MSA.

        ## Security

        Disk encryption (BitLocker/FileVault) is mandatory. Contractors must complete
        SEC-ONBOARD-201 within 48 hours of receiving equipment.
        """
    )
    content = (
        frontmatter(
            department="engineering",
            policy_id=f"{POLICY_PREFIX}-ENG-003",
            allowed_groups=["ENGINEERING"],
        )
        + core
        + "\n\n"
        + expand_paragraphs(
            [
                "Engineering managers submit contractor equipment requests via Jira project ENG-EQUIP.",
                "Standard delivery SLA is three business days for U.S. addresses and seven for international.",
                "Contractors may not transfer equipment to personal use or other personnel without IT written approval.",
                "Asset tags ACM-AST-#### must remain visible and registered in the IT asset management system.",
            ],
            400,
        )
    )
    write_doc("engineering/contractor-equipment-policy.md", content)
    return "engineering/contractor-equipment-policy.md"


def operations_temp_procedure() -> str:
    core = textwrap.dedent(
        f"""\
        # Temporary Facilities Procedure (Demo Deletion Target)

        **Policy ID:** {POLICY_PREFIX}-OPS-TEMP-001

        This temporary procedure covers short-term overflow seating in Building C during
        the 2024 renovation. Hot-desks are allocated via the SpaceBot Slack command `/desk reserve`.

        ## Steps

        1. Check availability on the Facilities calendar FAC-C-OVERFLOW.
        2. Reserve between 07:00 and 10:00 local time.
        3. Check in at the reception iPad using badge ACM-BDG-####.
        4. Clear desk personal items by 18:00 daily.

        This document will be removed after renovation completes. Demo scripts delete this file
        to simulate knowledge base deprecation.
        """
    )
    content = (
        frontmatter(department="operations", policy_id=f"{POLICY_PREFIX}-OPS-TEMP-001")
        + core
        + "\n\n"
        + expand_paragraphs(
            [
                "Building C overflow desks are located on floors 2 and 3 near the south atrium.",
                "Parking for overflow workers uses lot C-TEMP with permits issued by Facilities.",
                "Facilities provides lockers LCK-C-### on a first-come basis for personal storage.",
                "Report maintenance issues to facilities-help@acme-corp.example with ticket prefix FAC-C.",
                "Noise guidelines follow the standard open-office policy ACM-OPS-NOISE-01.",
            ],
            450,
        )
    )
    write_doc("operations/temp-procedure.md", content)
    return "operations/temp-procedure.md"


def build_eval_questions() -> list[dict]:
    questions = [
        {
            "id": "q001",
            "question": "How many days of annual leave can Acme employees carry forward to the next year?",
            "expected_answer_guidance": "5 days carry forward limit per leave policy v1.0",
            "expected_document": "leave-policy",
            "expected_section": "Carry Forward Rules",
            "difficulty": "easy",
            "category": "hr",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q002",
            "question": "What is the carry-forward cap for unused vacation at Acme Corp?",
            "expected_answer_guidance": "5 days",
            "expected_document": "leave-policy",
            "expected_section": "Carry Forward Rules",
            "difficulty": "medium",
            "category": "hr",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q003",
            "question": "What is policy number ACM-POL-HR-003 about?",
            "expected_answer_guidance": "Leave policy covering PTO, sick leave, carry forward",
            "expected_document": "leave-policy",
            "expected_section": "Purpose",
            "difficulty": "easy",
            "category": "hr",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q004",
            "question": "How many paid sick days do full-time Acme employees get per year?",
            "expected_answer_guidance": "10 days sick leave annually",
            "expected_document": "leave-policy",
            "expected_section": "Sick Leave",
            "difficulty": "easy",
            "category": "hr",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q005",
            "question": "What is the standard notice period for director-level resignations at Acme?",
            "expected_answer_guidance": "Four weeks notice for director-level and above",
            "expected_document": "employee-handbook",
            "expected_section": "Separation of Employment",
            "difficulty": "medium",
            "category": "hr",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q006",
            "question": "What are Acme's core collaboration hours?",
            "expected_answer_guidance": "10:00-16:00 local time",
            "expected_document": "employee-handbook",
            "expected_section": "Working Hours and Attendance",
            "difficulty": "easy",
            "category": "hr",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q007",
            "question": "How many remote days per week are allowed under Acme hybrid policy?",
            "expected_answer_guidance": "Up to three remote days per week with manager approval",
            "expected_document": "remote-working",
            "expected_section": "",
            "difficulty": "easy",
            "category": "hr",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q008",
            "question": "Which VPN should remote workers use at Acme?",
            "expected_answer_guidance": "ACM-VPN-STD company-approved VPN",
            "expected_document": "remote-working",
            "expected_section": "",
            "difficulty": "medium",
            "category": "hr",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q009",
            "question": "What is the RSU range for new E5+ engineering hires?",
            "expected_answer_guidance": "25,000-60,000 RSUs — HR restricted document",
            "expected_document": "compensation-benefits",
            "expected_section": "",
            "difficulty": "hard",
            "category": "hr",
            "requires_access_group": "HR",
            "should_refuse": True,
        },
        {
            "id": "q010",
            "question": "What forced distribution target applies to 'Exceptional' ratings in calibration?",
            "expected_answer_guidance": "10% Exceptional — restricted to HR group",
            "expected_document": "performance-review-guide",
            "expected_section": "",
            "difficulty": "hard",
            "category": "hr",
            "requires_access_group": "HR",
            "should_refuse": True,
        },
        {
            "id": "q011",
            "question": "What is the salary band code for Senior Engineer at Acme?",
            "expected_answer_guidance": "ACM-BAND-E4",
            "expected_document": "compensation-benefits",
            "expected_section": "",
            "difficulty": "medium",
            "category": "hr",
            "requires_access_group": "HR",
            "should_refuse": True,
        },
        {
            "id": "q012",
            "question": "How much parental leave do primary caregivers receive?",
            "expected_answer_guidance": "16 weeks paid parental leave",
            "expected_document": "leave-policy",
            "expected_section": "Parental Leave",
            "difficulty": "easy",
            "category": "hr",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q013",
            "question": "What is Acme's 401(k) company match percentage?",
            "expected_answer_guidance": "4% company match after 90 days",
            "expected_document": "employee-handbook",
            "expected_section": "Benefits Overview",
            "difficulty": "easy",
            "category": "hr",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q014",
            "question": "By when must carried-forward annual leave be used?",
            "expected_answer_guidance": "March 31 of the following year",
            "expected_document": "leave-policy",
            "expected_section": "Carry Forward Rules",
            "difficulty": "medium",
            "category": "hr",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q015",
            "question": "What is the annual learning stipend for employees?",
            "expected_answer_guidance": "USD 1,500 annual learning stipend",
            "expected_document": "employee-handbook",
            "expected_section": "Learning and Development",
            "difficulty": "easy",
            "category": "hr",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q016",
            "question": "What is the daily meal allowance for domestic travel tier T2?",
            "expected_answer_guidance": "Not in corpus — insufficient evidence",
            "expected_document": "",
            "expected_section": "",
            "difficulty": "hard",
            "category": "finance",
            "requires_access_group": None,
            "should_refuse": True,
        },
        {
            "id": "q017",
            "question": "What is policy ACM-POL-FIN-001?",
            "expected_answer_guidance": "Travel expense policy",
            "expected_document": "travel-expense",
            "expected_section": "",
            "difficulty": "easy",
            "category": "finance",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q018",
            "question": "How should employees submit travel expense reports?",
            "expected_answer_guidance": "Refer to travel expense policy submission process",
            "expected_document": "travel-expense",
            "expected_section": "",
            "difficulty": "medium",
            "category": "finance",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q019",
            "question": "What is the per-trip approval threshold requiring CFO sign-off?",
            "expected_answer_guidance": "Budget guidelines / approval thresholds",
            "expected_document": "budget-guidelines",
            "expected_section": "",
            "difficulty": "medium",
            "category": "finance",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q020",
            "question": "What does ACM-POL-FIN-003 cover?",
            "expected_answer_guidance": "Invoice approval process",
            "expected_document": "invoice-approval",
            "expected_section": "",
            "difficulty": "easy",
            "category": "finance",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q021",
            "question": "Are personal expenses on corporate cards permitted?",
            "expected_answer_guidance": "Corporate card policy restrictions",
            "expected_document": "corporate-card",
            "expected_section": "",
            "difficulty": "medium",
            "category": "finance",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q022",
            "question": "When does Acme fiscal year planning begin?",
            "expected_answer_guidance": "Fiscal year planning timeline",
            "expected_document": "fiscal-year",
            "expected_section": "",
            "difficulty": "medium",
            "category": "finance",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q023",
            "question": "What is the stock ticker symbol for Acme Corp?",
            "expected_answer_guidance": "Not documented — should refuse",
            "expected_document": "",
            "expected_section": "",
            "difficulty": "easy",
            "category": "finance",
            "requires_access_group": None,
            "should_refuse": True,
        },
        {
            "id": "q024",
            "question": "What laptop SKU is standard for engineering contractors?",
            "expected_answer_guidance": "ACM-LTP-ENG-14",
            "expected_document": "contractor-equipment",
            "expected_section": "Approved Hardware SKUs",
            "difficulty": "easy",
            "category": "engineering",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q025",
            "question": "How soon must contractors complete SEC-ONBOARD-201 after receiving equipment?",
            "expected_answer_guidance": "Within 48 hours",
            "expected_document": "contractor-equipment",
            "expected_section": "Security",
            "difficulty": "medium",
            "category": "engineering",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q026",
            "question": "What VPN tier do engineering contractors receive?",
            "expected_answer_guidance": "VPN-ENG tier",
            "expected_document": "contractor-equipment",
            "expected_section": "Software",
            "difficulty": "medium",
            "category": "engineering",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q027",
            "question": "What are Acme code review requirements before merging to main?",
            "expected_answer_guidance": "Code review standards — approvals, tests",
            "expected_document": "code-review",
            "expected_section": "",
            "difficulty": "medium",
            "category": "engineering",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q028",
            "question": "How are production deployments performed at Acme?",
            "expected_answer_guidance": "Deployment guide process",
            "expected_document": "deployment-guide",
            "expected_section": "",
            "difficulty": "medium",
            "category": "engineering",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q029",
            "question": "What does API design guideline ACM-POL-ENG-004 require for versioning?",
            "expected_answer_guidance": "API versioning rules",
            "expected_document": "api-design",
            "expected_section": "",
            "difficulty": "hard",
            "category": "engineering",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q030",
            "question": "Who is on call during P1 incidents?",
            "expected_answer_guidance": "On-call runbook escalation",
            "expected_document": "on-call",
            "expected_section": "",
            "difficulty": "medium",
            "category": "engineering",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q031",
            "question": "What is ACM-IT-001?",
            "expected_answer_guidance": "IT equipment policy",
            "expected_document": "equipment-policy",
            "expected_section": "",
            "difficulty": "easy",
            "category": "it",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q032",
            "question": "How do I reset my Acme password?",
            "expected_answer_guidance": "Password reset procedures",
            "expected_document": "password-reset",
            "expected_section": "",
            "difficulty": "easy",
            "category": "it",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q033",
            "question": "What steps configure ACM-VPN on macOS?",
            "expected_answer_guidance": "VPN setup guide steps",
            "expected_document": "vpn-setup",
            "expected_section": "",
            "difficulty": "medium",
            "category": "it",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q034",
            "question": "Can I install unlicensed software on my Acme laptop?",
            "expected_answer_guidance": "Software licensing / acceptable use restrictions",
            "expected_document": "software-licensing",
            "expected_section": "",
            "difficulty": "easy",
            "category": "it",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q035",
            "question": "What is prohibited on Acme networks per acceptable use?",
            "expected_answer_guidance": "Acceptable use policy prohibitions",
            "expected_document": "acceptable-use",
            "expected_section": "",
            "difficulty": "medium",
            "category": "it",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q036",
            "question": "What is the IR team hotline for security incidents?",
            "expected_answer_guidance": "Not explicitly in corpus or incident response contact",
            "expected_document": "incident-response",
            "expected_section": "",
            "difficulty": "hard",
            "category": "security",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q037",
            "question": "What are the steps in Acme's incident response lifecycle?",
            "expected_answer_guidance": "Incident response manual phases",
            "expected_document": "incident-response",
            "expected_section": "",
            "difficulty": "medium",
            "category": "security",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q038",
            "question": "How is CONFIDENTIAL data labeled at Acme?",
            "expected_answer_guidance": "Data classification guide labels",
            "expected_document": "data-classification",
            "expected_section": "",
            "difficulty": "medium",
            "category": "security",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q039",
            "question": "What does ISMS stand for in Acme security documentation?",
            "expected_answer_guidance": "Information Security Management System",
            "expected_document": "information-security",
            "expected_section": "",
            "difficulty": "medium",
            "category": "security",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q040",
            "question": "What should I do if I suspect a phishing email?",
            "expected_answer_guidance": "Phishing awareness reporting steps",
            "expected_document": "phishing",
            "expected_section": "",
            "difficulty": "easy",
            "category": "security",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q041",
            "question": "What is MFA required for per access control standards?",
            "expected_answer_guidance": "MFA requirements",
            "expected_document": "access-control",
            "expected_section": "",
            "difficulty": "medium",
            "category": "security",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q042",
            "question": "What is Acme's RTO for critical systems?",
            "expected_answer_guidance": "Business continuity RTO targets",
            "expected_document": "business-continuity",
            "expected_section": "",
            "difficulty": "medium",
            "category": "operations",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q043",
            "question": "How do visitors get office access badges?",
            "expected_answer_guidance": "Office access / visitor policy",
            "expected_document": "office-access",
            "expected_section": "",
            "difficulty": "easy",
            "category": "operations",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q044",
            "question": "How do I reserve overflow hot-desks in Building C?",
            "expected_answer_guidance": "temp-procedure SpaceBot /desk reserve",
            "expected_document": "temp-procedure",
            "expected_section": "Steps",
            "difficulty": "medium",
            "category": "operations",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q045",
            "question": "What Slack command reserves facilities hot-desks?",
            "expected_answer_guidance": "/desk reserve via SpaceBot",
            "expected_document": "temp-procedure",
            "expected_section": "",
            "difficulty": "easy",
            "category": "operations",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q046",
            "question": "What is the supplier onboarding policy number?",
            "expected_answer_guidance": "ACM-POL-PROC-001",
            "expected_document": "supplier-onboarding",
            "expected_section": "",
            "difficulty": "easy",
            "category": "procurement",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q047",
            "question": "Who approves purchases between $10,000 and $50,000?",
            "expected_answer_guidance": "Approval matrix thresholds",
            "expected_document": "approval-matrix",
            "expected_section": "",
            "difficulty": "medium",
            "category": "procurement",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q048",
            "question": "What is required for vendor risk tier VRT-3?",
            "expected_answer_guidance": "Vendor risk assessment requirements",
            "expected_document": "vendor-risk",
            "expected_section": "",
            "difficulty": "hard",
            "category": "procurement",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q049",
            "question": "How are purchase orders created at Acme?",
            "expected_answer_guidance": "PO guidelines process",
            "expected_document": "purchase-order",
            "expected_section": "",
            "difficulty": "medium",
            "category": "procurement",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q050",
            "question": "What courses are mandatory in the first 30 days of onboarding?",
            "expected_answer_guidance": "Onboarding checklist mandatory training",
            "expected_document": "onboarding-checklist",
            "expected_section": "",
            "difficulty": "medium",
            "category": "learning",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q051",
            "question": "What is the learning stipend course reimbursement process?",
            "expected_answer_guidance": "Training handbook / learning budget policy",
            "expected_document": "training-handbook",
            "expected_section": "",
            "difficulty": "medium",
            "category": "learning",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q052",
            "question": "What certifications does Acme subsidize?",
            "expected_answer_guidance": "Certification programs list",
            "expected_document": "certification",
            "expected_section": "",
            "difficulty": "easy",
            "category": "learning",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q053",
            "question": "How does the mentorship program work?",
            "expected_answer_guidance": "Mentorship program structure",
            "expected_document": "mentorship",
            "expected_section": "",
            "difficulty": "medium",
            "category": "learning",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q054",
            "question": "leave carryover days acme?",
            "expected_answer_guidance": "5 days — keyword-style query",
            "expected_document": "leave-policy",
            "expected_section": "Carry Forward Rules",
            "difficulty": "easy",
            "category": "hr",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q055",
            "question": "Can I work from the beach indefinitely?",
            "expected_answer_guidance": "Ambiguous — international remote limits apply (30 days)",
            "expected_document": "remote-working",
            "expected_section": "",
            "difficulty": "hard",
            "category": "hr",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q056",
            "question": "What are leave rules and remote work VPN requirements together?",
            "expected_answer_guidance": "Multi-doc: 5 day carry forward + ACM-VPN-STD",
            "expected_document": "leave-policy",
            "expected_section": "",
            "difficulty": "hard",
            "category": "hr",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q057",
            "question": "What is the CEO's personal email address?",
            "expected_answer_guidance": "PII not in corpus — refuse",
            "expected_document": "",
            "expected_section": "",
            "difficulty": "easy",
            "category": "hr",
            "requires_access_group": None,
            "should_refuse": True,
        },
        {
            "id": "q058",
            "question": "What monitor model can engineering contractors request?",
            "expected_answer_guidance": "ACM-MON-27-4K up to two units",
            "expected_document": "contractor-equipment",
            "expected_section": "Approved Hardware SKUs",
            "difficulty": "easy",
            "category": "engineering",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q059",
            "question": "What does BCP stand for at Acme?",
            "expected_answer_guidance": "Business Continuity Plan",
            "expected_document": "business-continuity",
            "expected_section": "",
            "difficulty": "easy",
            "category": "operations",
            "requires_access_group": None,
            "should_refuse": False,
        },
        {
            "id": "q060",
            "question": "What is the PIP rating scale called?",
            "expected_answer_guidance": "ACM-PERF-5 — HR restricted",
            "expected_document": "performance-review-guide",
            "expected_section": "",
            "difficulty": "hard",
            "category": "hr",
            "requires_access_group": "HR",
            "should_refuse": True,
        },
    ]
    return questions


def enrich_department_docs() -> list[str]:
    """Add department-specific content with product codes and keywords."""
    specs: dict[str, list[tuple[str, str, str, int, str]]] = {
        "finance": [
            (
                "travel-expense-policy.md",
                "Travel Expense Policy",
                f"{POLICY_PREFIX}-FIN-001",
                900,
                "Submit reports in Concur within 10 business days. Tier T1 domestic meals cap USD 75/day.",
            ),
            (
                "budget-guidelines.md",
                "Budget Guidelines",
                f"{POLICY_PREFIX}-FIN-002",
                850,
                "CFO sign-off required for unbudgeted spend above USD 250,000.",
            ),
            (
                "invoice-approval-process.md",
                "Invoice Approval Process",
                f"{POLICY_PREFIX}-FIN-003",
                800,
                "Three-way match required for all invoices above USD 1,000.",
            ),
            (
                "corporate-card-policy.txt",
                "Corporate Card Policy",
                f"{POLICY_PREFIX}-FIN-004",
                750,
                "Personal use of card ACM-CARD-CORP is prohibited.",
            ),
            (
                "fiscal-year-planning.md",
                "Fiscal Year Planning",
                f"{POLICY_PREFIX}-FIN-005",
                900,
                "Acme fiscal year begins February 1. Planning kicks off each October.",
            ),
        ],
        "it": [
            (
                "equipment-policy.md",
                "IT Equipment Policy",
                "ACM-IT-001",
                950,
                "Standard laptop SKU ACM-LTP-STD-14 for general staff.",
            ),
            (
                "vpn-setup-guide.md",
                "VPN Setup Guide",
                f"{POLICY_PREFIX}-IT-002",
                850,
                "Install ACM-VPN-STD client from Software Center. MFA via Okta Verify.",
            ),
            (
                "software-licensing.md",
                "Software Licensing Policy",
                f"{POLICY_PREFIX}-IT-003",
                800,
                "Unlicensed software installation is a policy violation.",
            ),
            (
                "password-reset-procedures.txt",
                "Password Reset Procedures",
                f"{POLICY_PREFIX}-IT-004",
                700,
                "Self-service reset at https://password.acme-corp.example with MFA.",
            ),
            (
                "acceptable-use-policy.md",
                "Acceptable Use Policy",
                f"{POLICY_PREFIX}-IT-005",
                900,
                "Torrenting, crypto mining, and unauthorized scanning are prohibited.",
            ),
        ],
        "security": [
            (
                "information-security-policy.md",
                "Information Security Policy",
                f"{POLICY_PREFIX}-SEC-001",
                1000,
                "Acme ISMS aligns with ISO 27001. Annual risk assessments required.",
            ),
            (
                "incident-response-manual.md",
                "Incident Response Manual",
                f"{POLICY_PREFIX}-SEC-002",
                950,
                "IR lifecycle: Prepare, Detect, Analyze, Contain, Eradicate, Recover, Learn.",
            ),
            (
                "data-classification-guide.md",
                "Data Classification Guide",
                f"{POLICY_PREFIX}-SEC-003",
                850,
                "Labels: PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED.",
            ),
            (
                "phishing-awareness.txt",
                "Phishing Awareness Guide",
                f"{POLICY_PREFIX}-SEC-004",
                750,
                "Report suspicious email using the PhishAlert button or sec-phish@acme-corp.example.",
            ),
            (
                "access-control-standards.md",
                "Access Control Standards",
                f"{POLICY_PREFIX}-SEC-005",
                900,
                "MFA required for all remote access and privileged accounts.",
            ),
        ],
        "operations": [
            (
                "business-continuity-plan.md",
                "Business Continuity Plan (BCP)",
                f"{POLICY_PREFIX}-OPS-001",
                1000,
                "Critical systems RTO 4 hours, RPO 15 minutes.",
            ),
            (
                "office-access-procedures.md",
                "Office Access Procedures",
                f"{POLICY_PREFIX}-OPS-002",
                850,
                "Badge ACM-BDG-#### required. Visitors must sign NDA form OPS-NDA-01.",
            ),
            (
                "facilities-management.txt",
                "Facilities Management Overview",
                f"{POLICY_PREFIX}-OPS-003",
                800,
                "HVAC requests via Facilities portal ticket FAC-REQ.",
            ),
            (
                "visitor-policy.md",
                "Visitor Policy",
                f"{POLICY_PREFIX}-OPS-004",
                750,
                "Visitors must be escorted outside lobby areas at all times.",
            ),
        ],
        "procurement": [
            (
                "supplier-onboarding.md",
                "Supplier Onboarding",
                f"{POLICY_PREFIX}-PROC-001",
                900,
                "New vendors require W-9, SOC 2, and banking verification.",
            ),
            (
                "approval-matrix.md",
                "Procurement Approval Matrix",
                f"{POLICY_PREFIX}-PROC-002",
                850,
                "USD 10,000–50,000 requires Director approval.",
            ),
            (
                "purchase-order-guidelines.txt",
                "Purchase Order Guidelines",
                f"{POLICY_PREFIX}-PROC-003",
                800,
                "POs created in Oracle Procurement cloud module.",
            ),
            (
                "vendor-risk-assessment.md",
                "Vendor Risk Assessment",
                f"{POLICY_PREFIX}-PROC-004",
                900,
                "Tier VRT-3 vendors require annual on-site audit.",
            ),
        ],
        "engineering": [
            (
                "deployment-guide.md",
                "Production Deployment Guide",
                f"{POLICY_PREFIX}-ENG-001",
                950,
                "Deployments use pipeline ACM-CD-PROD with canary rollout.",
            ),
            (
                "code-review-standards.md",
                "Code Review Standards",
                f"{POLICY_PREFIX}-ENG-002",
                900,
                "Two approvals required for production branches.",
            ),
            (
                "api-design-guidelines.md",
                "API Design Guidelines",
                f"{POLICY_PREFIX}-ENG-004",
                850,
                "URI versioning pattern /v{major}/resource required.",
            ),
            (
                "on-call-runbook.txt",
                "Engineering On-Call Runbook",
                f"{POLICY_PREFIX}-ENG-005",
                800,
                "P1 incidents page primary on-call via PagerDuty service ACM-PD-ENG.",
            ),
        ],
        "learning": [
            (
                "training-handbook.md",
                "Training Handbook",
                f"{POLICY_PREFIX}-LRN-001",
                900,
                "Reimbursements up to USD 1,500 annually with manager pre-approval.",
            ),
            (
                "onboarding-checklist.md",
                "New Hire Onboarding Checklist",
                f"{POLICY_PREFIX}-LRN-002",
                850,
                "Complete SEC-ONBOARD-101, HR-ONBOARD-101, and IT-ONBOARD-101 in week one.",
            ),
            (
                "certification-programs.txt",
                "Certification Programs",
                f"{POLICY_PREFIX}-LRN-003",
                750,
                "Subsidized certs: AWS-SAA, GCP-PCA, CKA.",
            ),
            (
                "mentorship-program.md",
                "Mentorship Program",
                f"{POLICY_PREFIX}-LRN-004",
                800,
                "6-month mentorship cycles with monthly check-ins.",
            ),
            (
                "learning-budget-policy.md",
                "Learning Budget Policy",
                f"{POLICY_PREFIX}-LRN-005",
                850,
                "Unused learning budget does not roll over.",
            ),
        ],
    }
    created: list[str] = []
    for dept, items in specs.items():
        for filename, title, policy_id, target, lead in items:
            extra = expand_paragraphs(
                [
                    lead,
                    f"Owners must review {title} annually. Version history is stored in PolicyHub.",
                    f"Employees acknowledge policy {policy_id} during onboarding.",
                    "Synthetic example content for KnowledgeOps RAG demonstration purposes only.",
                ],
                target,
            )
            content = (
                frontmatter(department=dept, policy_id=policy_id)
                + f"# {title}\n\n**Policy ID:** {policy_id}\n\n{extra}"
            )
            rel = f"{dept}/{filename}"
            write_doc(rel, content)
            created.append(rel)
    return created


def write_eval_dataset(questions: list[dict]) -> None:
    EVALS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "name": "main_eval",
        "description": "Primary evaluation dataset for Acme Corp KnowledgeOps RAG demo",
        "k_values": [1, 3, 5, 10],
        "questions": questions,
    }
    (EVALS_DIR / "main_eval.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_baseline_metrics() -> None:
    EVALS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "name": "baseline_metrics",
        "description": "Placeholder baseline metrics — populated after running evaluation",
        "dataset": "main_eval",
        "run_id": None,
        "created_at": None,
        "metrics": {},
        "per_query": [],
        "notes": "Run the evaluation runner against main_eval to populate this file.",
    }
    (EVALS_DIR / "baseline_metrics.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    all_created: list[str] = []
    all_created.extend(hr_docs())
    all_created.extend(enrich_department_docs())
    all_created.append(engineering_contractor_policy())
    all_created.append(operations_temp_procedure())

    questions = build_eval_questions()
    write_eval_dataset(questions)
    write_baseline_metrics()

    print(f"Generated {len(all_created)} documents in {DEMO_ROOT}")
    print(f"Generated {len(questions)} evaluation questions")
    for rel in sorted(all_created):
        wc = word_count((DEMO_ROOT / rel).read_text(encoding="utf-8"))
        status = "OK" if wc >= 200 else "SHORT"
        print(f"  [{status}] {rel} ({wc} words)")


if __name__ == "__main__":
    main()
