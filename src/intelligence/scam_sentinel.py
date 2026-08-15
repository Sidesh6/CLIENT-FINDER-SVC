"""
Scam Risk Sentinel & Freelance Fraud Detection Engine.
Identifies high-risk fraud patterns, off-platform payment schemes, and unpaid test traps.
"""

import logging
import re

from src.intelligence.schemas import (
    RedFlagTrigger,
    RiskTier,
    ScamAuditRequest,
    ScamAuditResult,
    ScamPatternType,
)

logger = logging.getLogger("ScamSentinel")


class ScamSentinel:
    """
    Automated fraud, payment scam, and exploitation sentinel for freelance project opportunities.
    """

    def audit_opportunity(self, req: ScamAuditRequest) -> ScamAuditResult:
        """
        Scan opportunity title, description, and metadata for malicious patterns and fraud indicators.
        """
        combined_text = f"{req.project_title} {req.project_description}".strip()
        lower_text = combined_text.lower()
        red_flags: list[RedFlagTrigger] = []

        # 1. Pattern: Off-Platform Payment Redirection
        off_platform_matches = re.findall(
            r"(telegram(?:\s+only|\s+me|\s+@|\s+id)?|whatsapp(?:\s+only|\s+me|\s+number)?|wire\s+transfer\s+directly|pay\s+outside\s+platform|direct\s+paypal\s+before\s+contract|zelle\s+me)",
            lower_text,
        )
        if off_platform_matches and any(
            t in lower_text for t in ["telegram", "whatsapp", "wire transfer", "zelle"]
        ):
            red_flags.append(
                RedFlagTrigger(
                    pattern_type=ScamPatternType.OFF_PLATFORM_PAYMENT,
                    severity="CRITICAL",
                    evidence_snippet=f"Detected off-platform contact redirection: {', '.join(set(off_platform_matches[:2]))}",
                    risk_explanation="Scammers frequently redirect developers to Telegram/WhatsApp to bypass platform escrow and buyer protections.",
                    defensive_action="Never communicate or accept payments off-platform without an established milestone contract or verified escrow.",
                )
            )

        # 2. Pattern: Fake Check Cashing / Equipment Purchasing Scam
        check_matches = re.findall(
            r"(send\s+you\s+a\s+check|cashier['\s]?s?\s+check|buy\s+(?:a\s+)?(?:laptop|equipment|macbook)\s+from\s+our\s+vendor|reimburse\s+you\s+by\s+check|deposit\s+this\s+check)",
            lower_text,
        )
        if check_matches:
            red_flags.append(
                RedFlagTrigger(
                    pattern_type=ScamPatternType.CHECK_CASHING_EQUIPMENT_SCAM,
                    severity="CRITICAL",
                    evidence_snippet=f"Check cashing phrase detected: '{check_matches[0]}'",
                    risk_explanation="Classic fake check scam: The check will bounce after you transfer funds to their 'approved equipment vendor'.",
                    defensive_action="IMMEDIATELY REJECT. Legitimate employers provide company hardware directly or use corporate procurement.",
                )
            )

        # 3. Pattern: Unpaid Multi-Day Test Task / Free Work Trap
        free_work_matches = re.findall(
            r"(unpaid\s+test|build\s+.*?\s+as\s+a\s+test|trial\s+task|prove\s+yourself\s+by\s+building|for\s+free\s+before|free\s+work)",
            lower_text,
        )
        if free_work_matches or (
            any(w in lower_text for w in ["for free", "unpaid", "trial task"])
            and any(t in lower_text for t in ["test", "app", "prove", "build", "assignment"])
        ):
            snippet = free_work_matches[0] if free_work_matches else "Unpaid evaluation task"
            red_flags.append(
                RedFlagTrigger(
                    pattern_type=ScamPatternType.FREE_WORK_TEST_TASK,
                    severity="HIGH",
                    evidence_snippet=f"Free work trigger detected: '{snippet}'",
                    risk_explanation="Client attempts to harvest free engineering labor disguised as an unpaid recruitment evaluation.",
                    defensive_action="Decline unpaid multi-day tasks. Offer a paid 5-hour exploratory spike or share existing portfolio repositories.",
                )
            )

        # 4. Pattern: Crypto / Unverified Smart Contract Fee
        crypto_scam_matches = re.findall(
            r"(pay\s+(?:a\s+)?registration\s+fee|deposit\s+(?:into\s+our\s+)?(?:smart\s+contract|wallet)\s+first|send\s+\d+\s*(?:usdt|eth|btc)\s+to\s+start|activate\s+your\s+vendor\s+account)",
            lower_text,
        )
        if crypto_scam_matches or (
            "smart contract" in lower_text
            and any(k in lower_text for k in ["deposit", "fee", "activate"])
        ):
            snippet = crypto_scam_matches[0] if crypto_scam_matches else "Upfront crypto deposit"
            red_flags.append(
                RedFlagTrigger(
                    pattern_type=ScamPatternType.CRYPTO_UNVERIFIED_ESCROW,
                    severity="CRITICAL",
                    evidence_snippet=f"Upfront crypto deposit trigger: '{snippet}'",
                    risk_explanation="Advance fee fraud requiring the freelancer to pay money upfront to 'activate' an account or contract.",
                    defensive_action="NEVER pay any upfront registration fee or crypto deposit to obtain client work.",
                )
            )

        # 5. Pattern: Unrealistic Budget vs. Scope Anomaly
        if req.claimed_budget:
            # Anomaly A: Unrealistically huge budget for trivial work (e.g. $80,000 for 1 html fix)
            trivial_keywords = ["fix typo", "minor css", "change button color", "1 hour task"]
            if any(t in lower_text for t in trivial_keywords) and req.claimed_budget > 10000.0:
                red_flags.append(
                    RedFlagTrigger(
                        pattern_type=ScamPatternType.UNREALISTIC_BUDGET_RATIO,
                        severity="HIGH",
                        evidence_snippet=f"Advertised budget (${req.claimed_budget:,.2f}) is abnormally inflated for trivial scope.",
                        risk_explanation="Inflated budgets for trivial tasks are often bait for phishing or check cashing schemes.",
                        defensive_action="Verify employer corporate identity and confirm payment escrow before initiating work.",
                    )
                )
            # Anomaly B: Severe underbudgeting for massive enterprise scope (e.g. $100 for Uber clone)
            massive_keywords = [
                "full uber clone",
                "complete amazon marketplace",
                "ai autonomous operating system",
            ]
            if any(m in lower_text for m in massive_keywords) and req.claimed_budget < 500.0:
                red_flags.append(
                    RedFlagTrigger(
                        pattern_type=ScamPatternType.UNREALISTIC_BUDGET_RATIO,
                        severity="WARNING",
                        evidence_snippet=f"Offered budget (${req.claimed_budget:,.2f}) is severely below minimum market engineering cost.",
                        risk_explanation="High likelihood of extreme scope creep, unpaid revisions, and client dissatisfaction.",
                        defensive_action="Propose a strict Phase 1 MVP Scope of Work or advise client on realistic market budgets.",
                    )
                )

        # Compute Composite Scam Risk Score (0-100)
        has_critical = any(f.severity == "CRITICAL" for f in red_flags)
        risk_score = 0.0
        for flag in red_flags:
            if flag.severity == "CRITICAL":
                risk_score += 75.0
            elif flag.severity == "HIGH":
                risk_score += 45.0
            elif flag.severity == "WARNING":
                risk_score += 20.0

        risk_score = min(100.0, risk_score)

        # Determine Categorical Risk Tier
        if has_critical or risk_score >= 70.0:
            tier = RiskTier.CRITICAL
            is_safe = False
        elif risk_score >= 40.0:
            tier = RiskTier.HIGH
            is_safe = False
        elif risk_score >= 15.0:
            tier = RiskTier.MEDIUM
            is_safe = True
        else:
            tier = RiskTier.LOW
            is_safe = True

        # Tactical recommendations
        recommendations = []
        if tier == RiskTier.CRITICAL:
            recommendations.append("[DANGER] DO NOT APPLY or send personal contact information.")
            recommendations.append("Flag posting as fraudulent on the source platform.")
            recommendations.append(
                "Never communicate on Telegram or WhatsApp for off-platform payment."
            )
        elif tier == RiskTier.HIGH:
            recommendations.append("[CAUTION] Proceed only with 100% funded platform escrow.")
            recommendations.append(
                "Do not commence active development without a signed Scope of Work."
            )
        elif tier == RiskTier.MEDIUM:
            recommendations.append("Use standard milestone schedule (30% upfront deposit).")
            recommendations.append("Enforce formal Change Order clauses to prevent scope creep.")
        else:
            recommendations.append(
                "[SAFE] Legitimate opportunity parameters. Safe to submit proposal."
            )

        confidence = 0.95 if red_flags else 0.85

        return ScamAuditResult(
            scam_risk_score=risk_score,
            risk_tier=tier,
            is_safe_to_apply=is_safe,
            detected_red_flags=red_flags,
            legitimacy_confidence=confidence,
            defensive_recommendations=recommendations,
        )


# Default Singleton Instance
GLOBAL_SCAM_SENTINEL = ScamSentinel()
