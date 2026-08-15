"""
Unit tests for Phase 25: AI Contract Generator & Legal Risk Analyzer (LegalTech Studio).
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.contracts.analyzer import GLOBAL_LEGAL_ANALYZER
from src.contracts.generator import GLOBAL_CONTRACT_GENERATOR
from src.contracts.registry import GLOBAL_CONTRACT_REGISTRY
from src.contracts.schemas import (
    AuditContractRequest,
    ContractStatus,
    ContractType,
    GenerateContractRequest,
    RiskCategory,
    RiskSeverity,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_contracts_state():
    """Reset contract registry singleton between tests."""
    GLOBAL_CONTRACT_REGISTRY._contracts.clear()
    GLOBAL_CONTRACT_REGISTRY._seq_counter.clear()


def test_contract_generator():
    req = GenerateContractRequest(
        contract_type=ContractType.MSA,
        client_name="Test Company",
        developer_name="Jane Doe",
        project_title="Cloud Migration API",
        payment_terms_days=14,
        retain_ip_until_paid=True,
    )
    markdown = GLOBAL_CONTRACT_GENERATOR.generate_contract_markdown(req)

    assert "MASTER SERVICES AGREEMENT" in markdown
    assert "Test Company" in markdown
    assert "Jane Doe" in markdown
    assert "Net 14" in markdown
    assert "ONLY UPON FULL AND FINAL PAYMENT" in markdown


def test_legal_risk_analyzer_traps():
    analyzer = GLOBAL_LEGAL_ANALYZER

    # Risk 1: Work made for hire without payment condition
    bad_text = "All work product shall be considered a work made for hire upon creation. Contractor assigns all rights including pre-existing tools and shall indemnify client for any and all claims without limitation of liability."
    result = analyzer.audit_contract(AuditContractRequest(contract_title="Trap Contract", contract_text=bad_text))

    assert result.overall_risk_score >= 50.0
    assert result.critical_count >= 1
    categories = [f.category for f in result.findings]
    assert RiskCategory.IP_ASSIGNMENT in categories
    assert RiskCategory.LIABILITY_LIMIT in categories


def test_contract_registry_lifecycle():
    req = GenerateContractRequest(
        contract_type=ContractType.SOW,
        client_name="Alpha LLC",
        developer_name="Bob Builder",
        project_title="FastAPI Service",
    )
    ctr = GLOBAL_CONTRACT_REGISTRY.create_contract("tenant_test", req)

    assert ctr.contract_number == "SOW-101"
    assert ctr.status == ContractStatus.DRAFT
    assert len(ctr.signatures) == 0
    assert not ctr.is_fully_executed

    # First signature -> PENDING_SIGNATURE
    updated1 = GLOBAL_CONTRACT_REGISTRY.sign_contract(ctr.id, "tenant_test", "Bob Builder", "bob@builder.io")
    assert updated1 is not None
    assert updated1.status == ContractStatus.PENDING_SIGNATURE
    assert len(updated1.signatures) == 1

    # Second signature -> EXECUTED
    updated2 = GLOBAL_CONTRACT_REGISTRY.sign_contract(ctr.id, "tenant_test", "Alice Client", "alice@alpha.com")
    assert updated2 is not None
    assert updated2.status == ContractStatus.EXECUTED
    assert len(updated2.signatures) == 2
    assert updated2.is_fully_executed


def test_contracts_api_routes():
    # Test POST /api/contracts/generate
    resp_gen = client.post(
        "/api/contracts/generate",
        json={
            "contract_type": "NDA",
            "client_name": "SecureCorp",
            "project_title": "Stealth AI Engine",
        },
    )
    assert resp_gen.status_code == 201
    data = resp_gen.json()
    assert data["contract_type"] == "NDA"
    assert data["client_name"] == "SecureCorp"
    c_id = data["id"]

    # Test GET /api/contracts
    resp_list = client.get("/api/contracts")
    assert resp_list.status_code == 200
    assert len(resp_list.json()) == 1

    # Test GET /api/contracts/{id}
    resp_get = client.get(f"/api/contracts/{c_id}")
    assert resp_get.status_code == 200
    assert resp_get.json()["id"] == c_id

    # Test POST /api/contracts/{id}/sign
    resp_sign = client.post(
        f"/api/contracts/{c_id}/sign",
        json={"signer_name": "Dev Signature", "signer_email": "dev@test.io"},
    )
    assert resp_sign.status_code == 200
    assert resp_sign.json()["status"] == "PENDING_SIGNATURE"

    # Test POST /api/contracts/audit
    resp_audit = client.post(
        "/api/contracts/audit",
        json={
            "contract_title": "Test Audit",
            "contract_text": "Developer agrees to indemnify client against all third party claims. Invoices paid Net 90.",
        },
    )
    assert resp_audit.status_code == 200
    audit_data = resp_audit.json()
    assert "overall_risk_score" in audit_data
    assert len(audit_data["findings"]) > 0
