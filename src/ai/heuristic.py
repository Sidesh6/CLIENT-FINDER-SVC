"""
Rule-based heuristic requirement extraction engine.
Provides deterministic, fast extraction of skills, budgets, categories,
and complexity when no LLM API key is configured or as a low-latency fallback.
"""

import re

from src.ai.schemas import (
    ExperienceLevel,
    ExtractedRequirements,
    PaymentType,
    ProjectCategory,
    ProjectComplexity,
)

# Comprehensive catalog mapping canonical skill names to regex patterns
SKILL_PATTERNS: dict[str, str] = {
    # AI & Machine Learning
    "LangChain": r"\blangchain\b",
    "LlamaIndex": r"\bllamaindex\b|\bllama-index\b",
    "RAG": r"\brag\b|\bretrieval[\s-]augmented\b",
    "OpenAI": r"\bopenai\b|\bgpt-?4\b|\bgpt-?3\.?5\b|\bchatgpt\b",
    "Anthropic": r"\banthropic\b|\bclaude\b",
    "Gemini": r"\bgemini\b|\bgoogle[\s-]ai\b",
    "PyTorch": r"\bpytorch\b|\btorch\b",
    "TensorFlow": r"\btensorflow\b|\bkeras\b",
    "HuggingFace": r"\bhugging[\s-]?face\b|\btransformers\b",
    "Vector Database": r"\bvector[\s-]db\b|\bpinecone\b|\bchromadb\b|\bweaviate\b|\bqdrant\b|\bmilvus\b",
    "LLM": r"\bllms?\b|\blarge[\s-]language[\s-]models?\b|\bprompt[\s-]engineering\b",
    "NLP": r"\bnlp\b|\bnatural[\s-]language[\s-]processing\b",
    "Computer Vision": r"\bcomputer[\s-]vision\b|\bopencv\b|\byolo\b",
    "Fine-Tuning": r"\bfine[\s-]tun(ing|ed)?\b|\blora\b|\bqlora\b",
    # Backend & Frameworks
    "Python": r"\bpython\b|\bpython3\b",
    "FastAPI": r"\bfastapi\b",
    "Django": r"\bdjango\b",
    "Flask": r"\bflask\b",
    "Node.js": r"\bnode(?:\.js)?\b|\bexpress(?:\.js)?\b|\bnest(?:\.js)?\b",
    "Go": r"\bgolang\b|\bgo\s+developer\b|\bgo\s+backend\b",
    "Rust": r"\brust\b|\brustlang\b",
    "Java": r"\bjava\b|\bspring[\s-]?boot\b",
    "C#": r"\bc#\b|\b\.net\b|\basp\.net\b",
    "C++": r"\bc\+\+\b",
    "PHP": r"\bphp\b|\blaravel\b|\bwordpress\b",
    "Ruby": r"\bruby\b|\brails\b|\bruby[\s-]on[\s-]rails\b",
    # Frontend
    "TypeScript": r"\btypescript\b|\bts\b",
    "JavaScript": r"\bjavascript\b|\bjs\b|\bes6\b",
    "React": r"\breact(?:\.js)?\b",
    "Next.js": r"\bnext(?:\.js)?\b",
    "Vue": r"\bvue(?:\.js)?\b|\bnuxt(?:\.js)?\b",
    "Angular": r"\bangular\b",
    "Svelte": r"\bsvelte\b|\bsveltekit\b",
    "TailwindCSS": r"\btailwind(?:\s*css)?\b",
    "GraphQL": r"\bgraphql\b",
    "HTML/CSS": r"\bhtml5?\b|\bcss3?\b|\bsass\b|\bscss\b",
    # Databases & Caching
    "PostgreSQL": r"\bpostgres(?:ql)?\b",
    "MySQL": r"\bmysql\b|\bmariadb\b",
    "MongoDB": r"\bmongodb\b|\bmongo\b",
    "Redis": r"\bredis\b",
    "SQLite": r"\bsqlite\b",
    "Snowflake": r"\bsnowflake\b",
    "BigQuery": r"\bbigquery\b",
    "SQL": r"\bsql\b|\bdatabase\b",
    # Cloud, DevOps & Infra
    "Docker": r"\bdocker\b|\bcontainer(s|ized)?\b",
    "Kubernetes": r"\bkubernetes\b|\bk8s\b",
    "AWS": r"\baws\b|\bamazon[\s-]web[\s-]services\b|\blambda\b|\bec2\b|\bs3\b",
    "GCP": r"\bgcp\b|\bgoogle[\s-]cloud\b",
    "Azure": r"\bazure\b",
    "Terraform": r"\bterraform\b",
    "CI/CD": r"\bci[\s/]?cd\b|\bgithub[\s-]actions\b|\bgitlab[\s-]ci\b",
    "Linux": r"\blinux\b|\bubuntu\b|\bbash\b",
    # Scraping & Automation
    "Web Scraping": r"\bscrap(ing|er|y)\b|\bcrawl(ing|er)\b|\bdata[\s-]extraction\b",
    "Playwright": r"\bplaywright\b",
    "Selenium": r"\bselenium\b",
    "BeautifulSoup": r"\bbeautifulsoup\b|\bbs4\b",
    # Mobile
    "React Native": r"\breact[\s-]native\b",
    "Flutter": r"\bflutter\b|\bdart\b",
    "iOS": r"\bios\b|\bswift\b|\bswiftui\b",
    "Android": r"\bandroid\b|\bkotlin\b",
}

# Regex for currency & budget discovery
CURRENCY_MAP = {
    "$": "USD",
    "usd": "USD",
    "€": "EUR",
    "eur": "EUR",
    "£": "GBP",
    "gbp": "GBP",
    "₹": "INR",
    "inr": "INR",
    "cad": "CAD",
    "aud": "AUD",
}

BUDGET_REGEXES = [
    # 1. Keyword prefix with range: "budget: $5,000 - $10,000" or "rate: $50 to $80"
    re.compile(
        r"(?:budget|rate|price|pay|compensation|fixed\s+price|salary)[:\s]+([$€£₹]|USD|EUR|GBP|INR)?\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(k|K)?\s*(?:-|to)\s*([$€£₹]|USD|EUR|GBP|INR)?\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(k|K)?\s*(USD|EUR|GBP|INR)?",
        re.IGNORECASE,
    ),
    # 2. Standalone range with leading currency: "$5,000 - $10,000" or "€1,000 - 2,000"
    re.compile(
        r"([$€£₹]|USD|EUR|GBP|INR)\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(k|K)?\s*(?:-|to)\s*([$€£₹]|USD|EUR|GBP|INR)?\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(k|K)?",
        re.IGNORECASE,
    ),
    # 3. Standalone range with trailing currency: "5,000 - 10,000 USD" or "500 - 1000 EUR"
    re.compile(
        r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(k|K)?\s*(?:-|to)\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(k|K)?\s*([$€£₹]|USD|EUR|GBP|INR)",
        re.IGNORECASE,
    ),
    # 4. Keyword prefix with single amount: "budget: $5,000" or "rate: $80"
    re.compile(
        r"(?:budget|rate|price|pay|compensation|fixed\s+price|salary)[:\s]+([$€£₹]|USD|EUR|GBP|INR)?\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(k|K)?\s*(USD|EUR|GBP|INR)?",
        re.IGNORECASE,
    ),
    # 5. Hourly rates: "$50/hr" or "$50 / hour" or "80 USD/hr"
    re.compile(
        r"([$€£₹]|USD|EUR|GBP|INR)?\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(k|K)?\s*(USD|EUR|GBP|INR)?\s*(?:/|\s+per\s+)\s*(?:hr|hour|hourly)",
        re.IGNORECASE,
    ),
    # 6. Single value with currency symbol: "$5000", "€2,500", "₹50,000"
    re.compile(
        r"([$€£₹]|USD|EUR|GBP|INR)\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(k|K)?",
        re.IGNORECASE,
    ),
]


class HeuristicExtractor:
    """
    Rule-based extractor identifying skills, compensation, complexity,
    and category classifications via pattern recognition.
    """

    def extract_skills(self, text: str) -> list[str]:
        """Match technologies against the comprehensive skill pattern catalog."""
        found_skills: list[str] = []
        for canonical_name, pattern in SKILL_PATTERNS.items():
            if re.search(pattern, text, re.IGNORECASE):
                found_skills.append(canonical_name)
        return found_skills

    def extract_budget(
        self, text: str
    ) -> tuple[float | None, float | None, str | None, PaymentType]:
        """
        Extract numeric budget min/max, ISO currency code, and payment type from text.
        """
        payment_type = PaymentType.UNKNOWN
        if re.search(r"\b(hourly|per hour|/hr|/hour|rate)\b", text, re.IGNORECASE):
            payment_type = PaymentType.HOURLY
        elif re.search(
            r"\b(fixed[\s-]price|flat[\s-]rate|milestone|project[\s-]based)\b", text, re.IGNORECASE
        ):
            payment_type = PaymentType.FIXED_PRICE
        elif re.search(r"\b(contract|contractor|month-to-month)\b", text, re.IGNORECASE):
            payment_type = PaymentType.CONTRACT
        elif re.search(r"\b(full[\s-]time|fte|permanent|salary)\b", text, re.IGNORECASE):
            payment_type = PaymentType.FULL_TIME

        # Search budget patterns
        for pattern in BUDGET_REGEXES:
            match = pattern.search(text)
            if match:
                groups = match.groups()
                # Determine currency
                currency = None
                for g in groups:
                    if g and g.strip().lower() in CURRENCY_MAP:
                        currency = CURRENCY_MAP[g.strip().lower()]
                        break
                    elif g and g.strip().upper() in {"USD", "EUR", "GBP", "INR", "CAD", "AUD"}:
                        currency = g.strip().upper()
                        break

                numbers: list[float] = []
                for g in groups:
                    if g and re.match(r"^\d{1,3}(?:,\d{3})*(?:\.\d+)?$", g.strip()):
                        val = float(g.replace(",", ""))
                        # Check multiplier
                        if "k" in match.group(0).lower() and val < 1000:
                            val *= 1000
                        numbers.append(val)

                if numbers:
                    if len(numbers) >= 2:
                        b_min, b_max = min(numbers), max(numbers)
                    else:
                        b_min, b_max = numbers[0], numbers[0]

                    if currency is None:
                        currency = "USD"  # Standard default if numeric symbol was omitted

                    return b_min, b_max, currency, payment_type

        return None, None, None, payment_type

    def classify_category(self, skills: list[str], text: str) -> ProjectCategory:
        """Classify high-level project category using skill density and keyword triggers."""
        text_lower = text.lower()

        ai_skills = {
            "LangChain",
            "LlamaIndex",
            "RAG",
            "OpenAI",
            "Anthropic",
            "Gemini",
            "PyTorch",
            "TensorFlow",
            "HuggingFace",
            "Vector Database",
            "LLM",
            "NLP",
            "Computer Vision",
            "Fine-Tuning",
        }
        scraping_skills = {"Web Scraping", "Playwright", "Selenium", "BeautifulSoup"}
        mobile_skills = {"React Native", "Flutter", "iOS", "Android"}
        data_skills = {"Snowflake", "BigQuery", "Kafka", "Airflow", "Spark"}
        web_skills = {
            "React",
            "Next.js",
            "Vue",
            "Angular",
            "Svelte",
            "Node.js",
            "FastAPI",
            "Django",
            "Flask",
            "TailwindCSS",
            "GraphQL",
        }
        devops_skills = {"Docker", "Kubernetes", "AWS", "GCP", "Azure", "Terraform", "CI/CD"}

        matched_skills = set(skills)
        if matched_skills & ai_skills or re.search(
            r"\b(ai|llm|gpt|agent|machine learning|generative ai)\b", text_lower
        ):
            return ProjectCategory.AI_DEVELOPMENT
        if matched_skills & scraping_skills or re.search(
            r"\b(scrape|scraper|crawling|extractor)\b", text_lower
        ):
            return ProjectCategory.AUTOMATION_SCRAPING
        if matched_skills & mobile_skills or re.search(
            r"\b(mobile app|ios app|android app)\b", text_lower
        ):
            return ProjectCategory.MOBILE_DEVELOPMENT
        if matched_skills & web_skills or re.search(
            r"\b(web app|fullstack|frontend|backend|rest api|website)\b", text_lower
        ):
            return ProjectCategory.WEB_DEVELOPMENT
        if matched_skills & data_skills or re.search(
            r"\b(data pipeline|etl|data warehouse|data engineer)\b", text_lower
        ):
            return ProjectCategory.DATA_ENGINEERING
        if matched_skills & devops_skills or re.search(
            r"\b(devops|infrastructure|cloud architecture)\b", text_lower
        ):
            return ProjectCategory.DEVOPS_CLOUD
        if matched_skills & {"Python", "Go", "Rust", "C++", "Java"}:
            return ProjectCategory.SYSTEMS_BACKEND

        return ProjectCategory.OTHER

    def estimate_complexity(self, skills: list[str], text: str) -> ProjectComplexity:
        """Estimate technical complexity level from skill count and architectural keywords."""
        high_complexity_terms = [
            "distributed",
            "high throughput",
            "low latency",
            "fine-tuning",
            "custom model",
            "microservices",
            "kubernetes",
            "architecture",
            "enterprise",
            "security audit",
        ]
        text_lower = text.lower()
        term_matches = sum(1 for term in high_complexity_terms if term in text_lower)

        if term_matches >= 2 or len(skills) >= 6:
            return ProjectComplexity.HIGH
        elif term_matches == 1 or len(skills) >= 3:
            return ProjectComplexity.MEDIUM
        elif len(skills) <= 2 and len(text) < 300:
            return ProjectComplexity.LOW
        else:
            return ProjectComplexity.MEDIUM

    def estimate_experience_level(self, text: str) -> ExperienceLevel:
        """Estimate required experience seniority."""
        text_lower = text.lower()
        if re.search(r"\b(lead|principal|architect|staff engineer|head of)\b", text_lower):
            return ExperienceLevel.LEAD
        if re.search(r"\b(senior|sr\.?|5\+\s*years|expert)\b", text_lower):
            return ExperienceLevel.SENIOR
        if re.search(r"\b(mid|intermediate|2-4\s*years)\b", text_lower):
            return ExperienceLevel.MID
        if re.search(r"\b(junior|jr\.?|entry[\s-]level|intern)\b", text_lower):
            return ExperienceLevel.JUNIOR
        return ExperienceLevel.NOT_SPECIFIED

    def extract_deliverables(self, text: str) -> list[str]:
        """Extract concrete bullet points or action sentences as deliverables."""
        deliverables: list[str] = []
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        for line in lines:
            if re.match(r"^[-*•\d\.)]\s+", line):
                clean_line = re.sub(r"^[-*•\d\.)]\s+", "", line).strip()
                if 10 < len(clean_line) < 150:
                    deliverables.append(clean_line)

        return deliverables[:5]

    def extract(self, title: str, description: str) -> ExtractedRequirements:
        """
        Perform complete heuristic requirement extraction on a title and description.
        """
        combined = f"{title}\n{description}"

        skills = self.extract_skills(combined)
        b_min, b_max, currency, payment_type = self.extract_budget(combined)
        category = self.classify_category(skills, combined)
        complexity = self.estimate_complexity(skills, combined)
        exp_level = self.estimate_experience_level(combined)
        deliverables = self.extract_deliverables(description)

        required_skills = skills
        optional_skills: list[str] = []

        summary = f"{title.strip()}. Project requiring {', '.join(skills[:3]) if skills else 'software development'}."

        return ExtractedRequirements(
            category=category,
            required_skills=required_skills,
            optional_skills=optional_skills,
            estimated_complexity=complexity,
            project_type=payment_type,
            experience_level=exp_level,
            budget_min=b_min,
            budget_max=b_max,
            currency=currency,
            deliverables=deliverables,
            technical_requirements=[f"Primary Stack: {', '.join(skills)}"] if skills else [],
            risk_signals=["Budget not explicitly defined"] if b_min is None else [],
            confidence_score=0.75 if skills else 0.50,
            summary=summary,
        )
