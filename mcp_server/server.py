from __future__ import annotations

from datetime import datetime, timezone
import os
import uuid

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("health-claims")


MOCK_MEMBERS = {
    "M-1001": {
        "member_id": "M-1001",
        "name": "Jordan Lee",
        "dob": "1983-04-12",
        "plan_id": "P-100",
        "group_id": "G-100",
        "coverage_effective": "2024-01-01",
    },
    "M-1002": {
        "member_id": "M-1002",
        "name": "Casey Patel",
        "dob": "1991-09-03",
        "plan_id": "P-200",
        "group_id": "G-200",
        "coverage_effective": "2024-03-01",
    },
}

MOCK_PLANS = {
    "P-100": {
        "plan_id": "P-100",
        "plan_name": "Optum Choice PPO",
        "deductible_total": 1500.0,
        "deductible_remaining": 420.0,
        "oop_max_total": 5000.0,
        "oop_max_remaining": 2100.0,
        "coinsurance_in_network": 0.2,
        "coinsurance_out_network": 0.4,
        "copay_primary": 30.0,
        "copay_specialist": 60.0,
    },
    "P-200": {
        "plan_id": "P-200",
        "plan_name": "Optum Select HMO",
        "deductible_total": 500.0,
        "deductible_remaining": 120.0,
        "oop_max_total": 3000.0,
        "oop_max_remaining": 980.0,
        "coinsurance_in_network": 0.1,
        "coinsurance_out_network": 0.5,
        "copay_primary": 20.0,
        "copay_specialist": 50.0,
    },
}

MOCK_PROVIDERS = {
    "PR-2001": {
        "provider_id": "PR-2001",
        "name": "Northside Primary Care",
        "npi": "1982745630",
        "specialty": "primary care",
        "network": "in-network",
        "zip_code": "55401",
    },
    "PR-2002": {
        "provider_id": "PR-2002",
        "name": "Lakeview Ortho Clinic",
        "npi": "1225487633",
        "specialty": "orthopedics",
        "network": "in-network",
        "zip_code": "55111",
    },
    "PR-2003": {
        "provider_id": "PR-2003",
        "name": "Metro Imaging Center",
        "npi": "1669234785",
        "specialty": "radiology",
        "network": "out-of-network",
        "zip_code": "55415",
    },
}

MOCK_CLAIMS = {
    "C-10001": {
        "claim_id": "C-10001",
        "member_id": "M-1001",
        "provider_id": "PR-2001",
        "service_date": "2024-08-10",
        "claim_type": "professional",
        "status": "paid",
        "status_reason": "adjudicated",
        "billed_amount": 250.0,
        "allowed_amount": 180.0,
        "paid_amount": 120.0,
        "member_responsibility": 60.0,
        "diagnosis_codes": ["E11.9"],
        "procedure_codes": ["99213"],
        "adjudication_date": "2024-08-18",
    },
    "C-10002": {
        "claim_id": "C-10002",
        "member_id": "M-1001",
        "provider_id": "PR-2003",
        "service_date": "2024-09-05",
        "claim_type": "diagnostic",
        "status": "pending",
        "status_reason": "awaiting medical records",
        "billed_amount": 980.0,
        "allowed_amount": 0.0,
        "paid_amount": 0.0,
        "member_responsibility": 0.0,
        "diagnosis_codes": ["M54.5"],
        "procedure_codes": ["72100"],
        "adjudication_date": None,
    },
    "C-10003": {
        "claim_id": "C-10003",
        "member_id": "M-1002",
        "provider_id": "PR-2002",
        "service_date": "2024-07-21",
        "claim_type": "professional",
        "status": "denied",
        "status_reason": "prior authorization required",
        "billed_amount": 1350.0,
        "allowed_amount": 0.0,
        "paid_amount": 0.0,
        "member_responsibility": 0.0,
        "diagnosis_codes": ["S83.511A"],
        "procedure_codes": ["29881"],
        "adjudication_date": "2024-07-30",
    },
}

MOCK_PRIOR_AUTHS = {
    "PA-9001": {
        "auth_id": "PA-9001",
        "member_id": "M-1002",
        "provider_id": "PR-2002",
        "procedure_codes": ["29881"],
        "diagnosis_codes": ["S83.511A"],
        "service_date": "2024-08-15",
        "status": "approved",
        "status_reason": "medical necessity met",
        "decision_date": "2024-07-25",
    }
}

INQUIRIES: list[dict] = []
NEXT_AUTH_ID = 9002


def _get_member(member_id: str) -> dict | None:
    return MOCK_MEMBERS.get(member_id)


def _get_provider(provider_id: str) -> dict | None:
    return MOCK_PROVIDERS.get(provider_id)


def _get_plan(plan_id: str) -> dict | None:
    return MOCK_PLANS.get(plan_id)


def _get_claim(claim_id: str) -> dict | None:
    return MOCK_CLAIMS.get(claim_id)


def _claim_summary(claim: dict) -> dict:
    provider = _get_provider(claim["provider_id"])
    return {
        "claim_id": claim["claim_id"],
        "service_date": claim["service_date"],
        "status": claim["status"],
        "status_reason": claim["status_reason"],
        "provider_name": provider["name"] if provider else "unknown",
        "billed_amount": claim["billed_amount"],
        "allowed_amount": claim["allowed_amount"],
        "member_responsibility": claim["member_responsibility"],
    }


def _estimate_costs(
    allowed_amount: float,
    deductible_remaining: float,
    coinsurance_rate: float,
    copay_amount: float,
) -> dict:
    applied_to_deductible = min(allowed_amount, deductible_remaining)
    after_deductible = max(allowed_amount - applied_to_deductible, 0.0)
    coinsurance = round(after_deductible * coinsurance_rate, 2)
    member_total = round(applied_to_deductible + coinsurance + copay_amount, 2)
    return {
        "applied_to_deductible": round(applied_to_deductible, 2),
        "coinsurance": coinsurance,
        "copay": round(copay_amount, 2),
        "member_responsibility_estimate": member_total,
    }


@mcp.tool()
def list_member_claims(member_id: str, status: str | None = None) -> dict:
    """List claims for a member, optionally filtered by status (paid, pending, denied)."""
    member = _get_member(member_id)
    if not member:
        return {"error": "member_not_found", "member_id": member_id}

    claims = [
        _claim_summary(claim)
        for claim in MOCK_CLAIMS.values()
        if claim["member_id"] == member_id
        and (status is None or claim["status"] == status)
    ]
    return {
        "member": {"member_id": member["member_id"], "name": member["name"]},
        "claim_count": len(claims),
        "claims": claims,
    }


@mcp.tool()
def get_claim_detail(claim_id: str) -> dict:
    """Get full claim detail including member, provider, and adjudication amounts."""
    claim = _get_claim(claim_id)
    if not claim:
        return {"error": "claim_not_found", "claim_id": claim_id}

    member = _get_member(claim["member_id"])
    provider = _get_provider(claim["provider_id"])
    return {
        **claim,
        "member": {"member_id": member["member_id"], "name": member["name"]}
        if member
        else None,
        "provider": provider,
    }


@mcp.tool()
def get_member_benefits(member_id: str) -> dict:
    """Return deductible and out-of-pocket balances for the member's plan."""
    member = _get_member(member_id)
    if not member:
        return {"error": "member_not_found", "member_id": member_id}

    plan = _get_plan(member["plan_id"])
    if not plan:
        return {"error": "plan_not_found", "plan_id": member["plan_id"]}

    return {
        "member_id": member_id,
        "plan": plan,
    }


@mcp.tool()
def estimate_member_responsibility(
    member_id: str,
    procedure_code: str,
    billed_amount: float,
    network: str = "in-network",
) -> dict:
    """Estimate member responsibility for a procedure based on plan and network."""
    member = _get_member(member_id)
    if not member:
        return {"error": "member_not_found", "member_id": member_id}

    plan = _get_plan(member["plan_id"])
    if not plan:
        return {"error": "plan_not_found", "plan_id": member["plan_id"]}

    if network not in {"in-network", "out-of-network"}:
        return {"error": "invalid_network", "network": network}

    allowed_multiplier = 0.75 if network == "in-network" else 0.6
    allowed_amount = round(billed_amount * allowed_multiplier, 2)
    coinsurance_rate = (
        plan["coinsurance_in_network"]
        if network == "in-network"
        else plan["coinsurance_out_network"]
    )
    copay_amount = plan["copay_specialist"] if procedure_code.startswith("99") else 0.0
    estimate = _estimate_costs(
        allowed_amount,
        plan["deductible_remaining"],
        coinsurance_rate,
        copay_amount,
    )
    return {
        "member_id": member_id,
        "procedure_code": procedure_code,
        "network": network,
        "billed_amount": round(billed_amount, 2),
        "allowed_amount_estimate": allowed_amount,
        "pricing_basis": "mock_allowed_amount",
        "estimate": estimate,
        "disclaimer": "Mock estimate only. Not a guarantee of payment.",
    }


@mcp.tool()
def search_providers(
    specialty: str, zip_code: str | None = None, network: str | None = None
) -> list[dict]:
    """Search providers by specialty, with optional zip code and network filters."""
    results = []
    specialty_lower = specialty.lower()
    for provider in MOCK_PROVIDERS.values():
        if specialty_lower not in provider["specialty"]:
            continue
        if zip_code and provider["zip_code"] != zip_code:
            continue
        if network and provider["network"] != network:
            continue
        results.append(provider)
    return results


@mcp.tool()
def create_prior_authorization(
    member_id: str,
    provider_id: str,
    procedure_codes: list[str],
    service_date: str,
    diagnosis_codes: list[str] | None = None,
) -> dict:
    """Create a mock prior authorization request and return the tracking id."""
    global NEXT_AUTH_ID

    member = _get_member(member_id)
    provider = _get_provider(provider_id)
    if not member:
        return {"error": "member_not_found", "member_id": member_id}
    if not provider:
        return {"error": "provider_not_found", "provider_id": provider_id}

    auth_id = f"PA-{NEXT_AUTH_ID}"
    NEXT_AUTH_ID += 1
    record = {
        "auth_id": auth_id,
        "member_id": member_id,
        "provider_id": provider_id,
        "procedure_codes": procedure_codes,
        "diagnosis_codes": diagnosis_codes or [],
        "service_date": service_date,
        "status": "pending",
        "status_reason": "clinical review",
        "decision_date": None,
    }
    MOCK_PRIOR_AUTHS[auth_id] = record
    return record


@mcp.tool()
def get_prior_authorization_status(auth_id: str) -> dict:
    """Fetch the current status of a prior authorization request."""
    record = MOCK_PRIOR_AUTHS.get(auth_id)
    if not record:
        return {"error": "auth_not_found", "auth_id": auth_id}
    return record


@mcp.tool()
def submit_claim_inquiry(claim_id: str, inquiry_type: str, note: str) -> dict:
    """Submit a mock claim inquiry and return a ticket reference."""
    claim = _get_claim(claim_id)
    if not claim:
        return {"error": "claim_not_found", "claim_id": claim_id}

    ticket_id = f"INQ-{uuid.uuid4().hex[:8].upper()}"
    record = {
        "ticket_id": ticket_id,
        "claim_id": claim_id,
        "inquiry_type": inquiry_type,
        "note": note,
        "submitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": "open",
    }
    INQUIRIES.append(record)
    return record


if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    mount_path = os.getenv("MCP_MOUNT_PATH")
    mcp.run(transport=transport, mount_path=mount_path)
