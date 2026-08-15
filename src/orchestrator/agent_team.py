from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Final


MATERIAL_AUTHORITIES: Final[frozenset[str]] = frozenset(
    {"approve_grant", "approve_spec", "commit", "deploy", "spend", "mutate"}
)


@dataclass(frozen=True)
class AgentPolicy:
    profile: str
    function: str
    responsibilities: tuple[str, ...]
    authorities: frozenset[str] = frozenset()

    def public_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["authorities"] = sorted(self.authorities)
        return data


@dataclass(frozen=True)
class WorkflowStep:
    order: int
    profile: str
    responsibility: str
    parallel_group: str | None = None


@dataclass(frozen=True)
class ReportRequest:
    requester: str
    target: str
    subject: str
    report_only: bool = True
    authorities: frozenset[str] = frozenset()


_POLICIES: Final[tuple[AgentPolicy, ...]] = (
    AgentPolicy("alfred", "personal_assistant", (
        "request and consolidate reports", "track decisions and pending work",
    ), frozenset({"request_report"})),
    AgentPolicy("spock", "final_decision_owner", (
        "consolidate and approve specifications", "approve reserve grants",
        "make final architecture and go/no-go decisions",
    ), frozenset({"approve_grant", "approve_spec"})),
    AgentPolicy("b-elanna", "backend_engineer", (
        "validate technical feasibility of specifications",
        "implement backend, API, service, integration and scoped refactoring work",
    )),
    AgentPolicy("seven", "research_analyst", (
        "research alternatives", "identify specification gaps and risks",
    )),
    AgentPolicy("troi", "requirements_analyst", (
        "validate intent, scope and acceptance criteria", "assess user impact",
    )),
    AgentPolicy("la-forge", "complex_systems_engineer", (
        "lead complex distributed implementation work",
        "coordinate shared architecture, concurrency, API and schema boundaries",
    )),
    AgentPolicy("barclay", "diagnostic_engineer", (
        "reproduce bugs and isolate root causes", "execute the initial Flash pilot",
    )),
    AgentPolicy("rutherford", "test_engineer", (
        "validate tests, regression, CI and evidence", "verify integrated workstreams",
    )),
    AgentPolicy("tuvok", "independent_reviewer", (
        "perform independent security review", "revoke grants in an emergency",
    ), frozenset({"revoke_grant"})),
    AgentPolicy("obrien", "operations_engineer", (
        "operate deployments and incidents", "activate the reserve kill switch",
        "revoke grants in an emergency",
    ), frozenset({"operate", "revoke_grant"})),
    AgentPolicy("data", "data_and_finance_analyst", (
        "reconcile reserve spend", "maintain ledger and financial evidence",
    )),
    AgentPolicy("bashir", "database_safety_reviewer", (
        "review migrations, backups and restores", "protect data recovery controls",
    )),
    AgentPolicy("uhura", "documentation_specialist", (
        "document pilot decisions and evidence", "verify communication accuracy",
    )),
    AgentPolicy("crusher", "clinical_governance", (
        "govern clinical safety and critical healthcare decisions",
    )),
    AgentPolicy("default", "general_assistant", (
        "route general requests to the appropriate specialist",
    )),
)

AGENT_POLICIES: Final[dict[str, AgentPolicy]] = {
    policy.profile: policy for policy in _POLICIES
}

SPEC_REVIEW_WORKFLOW: Final[tuple[WorkflowStep, ...]] = (
    WorkflowStep(1, "seven", "research gaps, risks and alternatives"),
    WorkflowStep(2, "troi", "validate intent, scope and acceptance criteria"),
    WorkflowStep(3, "b-elanna", "validate technical feasibility and propose changes"),
    WorkflowStep(4, "spock", "consolidate proposals and decide the final specification"),
)

PARALLEL_IMPLEMENTATION_WORKFLOW: Final[tuple[WorkflowStep, ...]] = (
    WorkflowStep(1, "spock", "partition approved work into independent scopes"),
    WorkflowStep(2, "la-forge", "lead the most complex implementation workstream", "implementation"),
    WorkflowStep(2, "b-elanna", "implement scoped backend and integration work", "implementation"),
    WorkflowStep(2, "barclay", "diagnose and implement small isolated fixes", "implementation"),
    WorkflowStep(2, "data", "implement data, SQL and ledger work", "implementation"),
    WorkflowStep(3, "rutherford", "validate integration, regression and evidence"),
    WorkflowStep(4, "tuvok", "perform independent review"),
    WorkflowStep(5, "spock", "make the final decision"),
)

RESERVE_OWNERS: Final[dict[str, tuple[str, ...]]] = {
    "specification": ("spock", "b-elanna", "seven", "troi"),
    "grant_and_final_decision": ("spock",),
    "operations_incident_kill_switch": ("obrien",),
    "independent_security_review": ("tuvok",),
    "finance_ledger_reconciliation": ("data",),
    "migration_backup_restore": ("bashir",),
    "tests_and_evidence": ("rutherford",),
    "documentation": ("uhura",),
    "initial_flash_pilot": ("barclay",),
    "emergency_revocation": ("spock", "tuvok", "obrien"),
}


def get_agent_policy(profile: str) -> AgentPolicy:
    try:
        return AGENT_POLICIES[profile]
    except KeyError as exc:
        raise ValueError(f"unknown agent profile {profile!r}") from exc


def can_authorize(profile: str, authority: str) -> bool:
    if authority not in MATERIAL_AUTHORITIES and authority not in {
        "operate", "request_report", "revoke_grant",
    }:
        return False
    return authority in get_agent_policy(profile).authorities


def request_report(requester: str, target: str, subject: str) -> ReportRequest:
    if requester != "alfred" or not can_authorize(requester, "request_report"):
        raise PermissionError("only Alfred may use personal report coordination")
    get_agent_policy(target)
    normalized_subject = subject.strip()
    if not normalized_subject:
        raise ValueError("report subject must not be empty")
    return ReportRequest(requester, target, normalized_subject)
