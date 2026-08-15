"""
Contract Registry — In-Memory Storage, Contract Lifecycle Manager, and E-Signature Ledger.
"""

import hashlib
import logging
import uuid
from datetime import UTC, date, datetime

from src.contracts.generator import GLOBAL_CONTRACT_GENERATOR
from src.contracts.schemas import (
    ContractRecord,
    ContractStatus,
    ContractType,
    GenerateContractRequest,
    SignatureRecord,
)

logger = logging.getLogger("ContractRegistry")


class ContractRegistry:
    """
    Central repository managing stored agreements, e-signatures, and lifecycle status transitions.
    """

    def __init__(self) -> None:
        self._contracts: dict[str, ContractRecord] = {}
        self._seq_counter: dict[str, int] = {}
        self._seed_demo_contracts()

    def _next_contract_number(self, tenant_id: str, c_type: ContractType) -> str:
        self._seq_counter[tenant_id] = self._seq_counter.get(tenant_id, 100) + 1
        prefix = c_type.value
        return f"{prefix}-{self._seq_counter[tenant_id]}"

    def _seed_demo_contracts(self) -> None:
        """Seed initial contracts for instant dashboard demo exploration."""
        tenant_id = "default_tenant"
        now = datetime.now(UTC)
        today = date.today()

        # Demo 1: MSA
        msa_req = GenerateContractRequest(
            contract_type=ContractType.MSA,
            client_name="Acme Corp",
            developer_name="Alex Mercer (Lead Fullstack Dev)",
            project_title="Fullstack Web & Mobile Platform",
            governing_state_country="Delaware, USA",
            payment_terms_days=14,
            retain_ip_until_paid=True,
            liability_cap_usd=25000.0,
        )
        msa_text = GLOBAL_CONTRACT_GENERATOR.generate_contract_markdown(msa_req)
        msa_id = "ctr_demo_001"
        msa = ContractRecord(
            id=msa_id,
            contract_number="MSA-101",
            tenant_id=tenant_id,
            contract_type=ContractType.MSA,
            title="Master Services Agreement — Acme Corp",
            client_name="Acme Corp",
            developer_name="Alex Mercer",
            status=ContractStatus.EXECUTED,
            content_markdown=msa_text,
            effective_date=date.fromordinal(today.toordinal() - 45),
            signatures=[
                SignatureRecord(
                    signature_id="sig_001",
                    signer_name="Alex Mercer",
                    signer_email="alex@mercerdev.io",
                    signed_at=now,
                    verification_hash=hashlib.sha256(b"Alex Mercer MSA-101").hexdigest()[:16],
                ),
                SignatureRecord(
                    signature_id="sig_002",
                    signer_name="John Wiley (VP Engineering, Acme)",
                    signer_email="jwiley@acme.com",
                    signed_at=now,
                    verification_hash=hashlib.sha256(b"John Wiley MSA-101").hexdigest()[:16],
                ),
            ],
            created_at=now,
            updated_at=now,
        )
        self._contracts[msa_id] = msa

        # Demo 2: SOW
        sow_req = GenerateContractRequest(
            contract_type=ContractType.SOW,
            client_name="NovaTech Solutions",
            developer_name="Alex Mercer",
            project_title="Next.js E-Commerce Frontend & Stripe Integration",
            payment_terms_days=30,
        )
        sow_text = GLOBAL_CONTRACT_GENERATOR.generate_contract_markdown(sow_req)
        sow_id = "ctr_demo_002"
        sow = ContractRecord(
            id=sow_id,
            contract_number="SOW-102",
            tenant_id=tenant_id,
            contract_type=ContractType.SOW,
            title="SOW — Next.js E-Commerce Frontend",
            client_name="NovaTech Solutions",
            developer_name="Alex Mercer",
            status=ContractStatus.PENDING_SIGNATURE,
            content_markdown=sow_text,
            effective_date=today,
            signatures=[
                SignatureRecord(
                    signature_id="sig_003",
                    signer_name="Alex Mercer",
                    signer_email="alex@mercerdev.io",
                    signed_at=now,
                    verification_hash=hashlib.sha256(b"Alex Mercer SOW-102").hexdigest()[:16],
                )
            ],
            created_at=now,
            updated_at=now,
        )
        self._contracts[sow_id] = sow

    def create_contract(self, tenant_id: str, req: GenerateContractRequest) -> ContractRecord:
        """Generate and store a new contract."""
        now = datetime.now(UTC)
        today = req.effective_date or date.today()
        c_id = f"ctr_{uuid.uuid4().hex[:10]}"
        number = self._next_contract_number(tenant_id, req.contract_type)
        markdown = GLOBAL_CONTRACT_GENERATOR.generate_contract_markdown(req)

        contract = ContractRecord(
            id=c_id,
            contract_number=number,
            tenant_id=tenant_id,
            contract_type=req.contract_type,
            title=f"{req.contract_type.value} — {req.project_title}",
            client_name=req.client_name,
            developer_name=req.developer_name,
            status=ContractStatus.DRAFT,
            content_markdown=markdown,
            effective_date=today,
            created_at=now,
            updated_at=now,
        )
        self._contracts[c_id] = contract
        logger.info("Created contract %s for client '%s'", number, req.client_name)
        return contract

    def list_contracts(self, tenant_id: str, status_filter: ContractStatus | None = None) -> list[ContractRecord]:
        """List all contracts for tenant, sorted by effective date."""
        items = [c for c in self._contracts.values() if c.tenant_id == tenant_id]
        if status_filter:
            items = [c for c in items if c.status == status_filter]
        return sorted(items, key=lambda x: x.effective_date, reverse=True)

    def get_contract(self, contract_id: str) -> ContractRecord | None:
        return self._contracts.get(contract_id)

    def sign_contract(
        self,
        contract_id: str,
        tenant_id: str,
        signer_name: str,
        signer_email: str,
    ) -> ContractRecord | None:
        """Record an e-signature against a contract."""
        contract = self._contracts.get(contract_id)
        if not contract or contract.tenant_id != tenant_id:
            return None

        now = datetime.now(UTC)
        sig_id = f"sig_{uuid.uuid4().hex[:8]}"
        hash_seed = f"{signer_name}:{signer_email}:{contract.contract_number}:{now.isoformat()}"
        verification_hash = hashlib.sha256(hash_seed.encode()).hexdigest()[:16]

        sig = SignatureRecord(
            signature_id=sig_id,
            signer_name=signer_name,
            signer_email=signer_email,
            signed_at=now,
            ip_address="127.0.0.1",
            verification_hash=verification_hash,
        )
        contract.signatures.append(sig)
        contract.updated_at = now

        if len(contract.signatures) == 1:
            contract.status = ContractStatus.PENDING_SIGNATURE
        elif len(contract.signatures) >= 2:
            contract.status = ContractStatus.EXECUTED

        logger.info("Recorded signature by '%s' on contract %s (status: %s)", signer_name, contract.contract_number, contract.status.value)
        return contract


GLOBAL_CONTRACT_REGISTRY = ContractRegistry()
