"""
AI Contract Generator Engine — Dynamic Legal Template Synthesizer for MSAs, SOWs, and NDAs.
"""

import logging
from datetime import date, datetime

from src.contracts.schemas import ContractType, GenerateContractRequest

logger = logging.getLogger("ContractGeneratorEngine")


class ContractGeneratorEngine:
    """
    Generates standardized, protective freelance legal agreements with dynamic clause configuration.
    """

    def generate_contract_markdown(self, req: GenerateContractRequest) -> str:
        """Generate markdown formatted legal text based on request parameters."""
        eff_date = req.effective_date or date.today()
        eff_str = eff_date.strftime("%B %d, %Y")

        if req.contract_type == ContractType.MSA:
            return self._generate_msa(req, eff_str)
        elif req.contract_type == ContractType.SOW:
            return self._generate_sow(req, eff_str)
        elif req.contract_type == ContractType.NDA:
            return self._generate_nda(req, eff_str)
        else:
            return self._generate_contractor_agreement(req, eff_str)

    def _generate_msa(self, req: GenerateContractRequest, eff_str: str) -> str:
        ip_clause = (
            "All Intellectual Property Rights in deliverables developed under this Agreement shall transfer to Client "
            "ONLY UPON FULL AND FINAL PAYMENT of all applicable invoices. Developer retains a non-exclusive lien on all work product until paid in full."
            if req.retain_ip_until_paid
            else "Developer assigns all IP rights upon deliverable completion."
        )

        return f"""# MASTER SERVICES AGREEMENT (MSA)

**THIS MASTER SERVICES AGREEMENT** (the "Agreement") is entered into effective as of **{eff_str}** by and between:

- **Developer / Contractor**: {req.developer_name} ("Developer")
- **Client**: {req.client_name} ("Client")

---

### 1. SERVICES & STATEMENTS OF WORK
Developer agrees to perform software development, engineering, or consulting services as defined in mutually executed Statements of Work ("SOW") governed by this Agreement.

### 2. COMPENSATION & PAYMENT TERMS
- Invoices shall be submitted by Developer according to milestone completion or hourly tracking.
- Client agrees to settle all valid invoices within **{req.payment_terms_days} calendar days** of issuance ("Net {req.payment_terms_days}").
- Overdue payments shall accrue interest at the rate of 1.5% per month (18% per annum) or the maximum legal rate.

### 3. INTELLECTUAL PROPERTY RIGHTS
{ip_clause}

### 4. LIMITATION OF LIABILITY
TO THE MAXIMUM EXTENT PERMITTED BY LAW, DEVELOPER'S AGGREGATE LIABILITY ARISING OUT OF OR RELATED TO THIS AGREEMENT SHALL NOT EXCEED **${req.liability_cap_usd:,.2f}** OR THE TOTAL FEES PAID BY CLIENT IN THE THREE (3) MONTHS PRECEDING THE CLAIM. IN NO EVENT SHALL DEVELOPER BE LIABLE FOR CONSEQUENTIAL, INDIRECT, OR PUNATIVE DAMAGES.

### 5. TERMINATION
Either party may terminate this Agreement or any active SOW for convenience by providing at least **{req.termination_notice_days} days written notice** to the other party. Upon termination, Client shall immediately pay Developer for all services rendered up to the effective termination date.

### 6. GOVERNING LAW & JURISDICTION
This Agreement shall be governed by and construed in accordance with the laws of **{req.governing_state_country}**, without regard to its conflict of law principles.

---

**IN WITNESS WHEREOF**, the parties have executed this Master Services Agreement as of the date first written above.

**DEVELOPER**: {req.developer_name}  
**CLIENT**: {req.client_name}  
"""

    def _generate_sow(self, req: GenerateContractRequest, eff_str: str) -> str:
        return f"""# STATEMENT OF WORK (SOW)

**SOW PROJECT**: {req.project_title}  
**EFFECTIVE DATE**: {eff_str}  

---

### 1. PROJECT OVERVIEW & SCOPE
Developer ({req.developer_name}) will design, implement, and deploy **{req.project_title}** for Client ({req.client_name}).

### 2. DELIVERABLES & MILESTONES
- **Phase 1**: System Architecture & Database Schema Specification
- **Phase 2**: Core Feature Implementation & REST API Routes
- **Phase 3**: User Acceptance Testing & Staging Deployment

### 3. PAYMENT SCHEDULE
- Total Project Amount: As specified in invoice schedule.
- Payment Terms: **Net {req.payment_terms_days} days**.
- Intellectual Property transfer is subject to full payment settlement.

---

**GOVERNING MSA**: Governed by Master Services Agreement between {req.developer_name} and {req.client_name}.
"""

    def _generate_nda(self, req: GenerateContractRequest, eff_str: str) -> str:
        return f"""# MUTUAL NON-DISCLOSURE AGREEMENT (NDA)

**EFFECTIVE DATE**: {eff_str}  
**PARTIES**: {req.developer_name} and {req.client_name}  

---

### 1. CONFIDENTIAL INFORMATION
"Confidential Information" refers to any proprietary technical, financial, or business information shared between the parties for the purpose of evaluating and executing **{req.project_title}**.

### 2. OBLIGATIONS OF CONFIDENTIALITY
Each party agrees to hold the other party's Confidential Information in strict confidence and shall not disclose it to any third party without prior written consent.

### 3. DURATION
The confidentiality obligations under this Agreement shall remain in effect for a period of **two (2) years** from the date of disclosure.

### 4. GOVERNING LAW
Governed by the laws of **{req.governing_state_country}**.
"""

    def _generate_contractor_agreement(self, req: GenerateContractRequest, eff_str: str) -> str:
        return f"""# INDEPENDENT CONTRACTOR AGREEMENT

**EFFECTIVE DATE**: {eff_str}  
**CONTRACTOR**: {req.developer_name}  
**COMPANY**: {req.client_name}  

---

### 1. INDEPENDENT CONTRACTOR STATUS
Contractor is an independent contractor and not an employee, agent, or partner of Company. Contractor is solely responsible for all federal, state, and local taxes on income earned.

### 2. SCOPE & COMPENSATION
Contractor agrees to perform engineering work for **{req.project_title}**. Invoices shall be paid within **{req.payment_terms_days} days**.

### 3. INTELLECTUAL PROPERTY & LIABILITY
Work product belongs to Company upon full payment. Contractor liability is capped at **${req.liability_cap_usd:,.2f}**.

### 4. GOVERNING LAW
Governed by **{req.governing_state_country}**.
"""


GLOBAL_CONTRACT_GENERATOR = ContractGeneratorEngine()
