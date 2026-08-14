"""
Skill taxonomy, synonym normalization, and related skill ontology graph.
"""

# Alias and synonym mapping to canonical technology names
SYNONYM_MAP: dict[str, str] = {
    # AI & ML
    "langchain": "LangChain",
    "llamaindex": "LlamaIndex",
    "llama-index": "LlamaIndex",
    "rag": "RAG",
    "retrieval augmented generation": "RAG",
    "retrieval-augmented generation": "RAG",
    "openai": "OpenAI",
    "chatgpt": "OpenAI",
    "gpt-4": "OpenAI",
    "gpt-4o": "OpenAI",
    "gpt-3.5": "OpenAI",
    "gpt": "OpenAI",
    "anthropic": "Anthropic",
    "claude": "Anthropic",
    "claude 3": "Anthropic",
    "gemini": "Gemini",
    "google ai": "Gemini",
    "llm": "LLM",
    "llms": "LLM",
    "large language model": "LLM",
    "large language models": "LLM",
    "vector db": "Vector Database",
    "vectordb": "Vector Database",
    "pinecone": "Vector Database",
    "chromadb": "Vector Database",
    "chroma": "Vector Database",
    "weaviate": "Vector Database",
    "qdrant": "Vector Database",
    "milvus": "Vector Database",
    "pytorch": "PyTorch",
    "torch": "PyTorch",
    "tensorflow": "TensorFlow",
    "keras": "TensorFlow",
    "huggingface": "HuggingFace",
    "transformers": "HuggingFace",
    "nlp": "NLP",
    "natural language processing": "NLP",
    "fine-tuning": "Fine-Tuning",
    "lora": "Fine-Tuning",
    # Backend & Languages
    "python": "Python",
    "python3": "Python",
    "py": "Python",
    "fastapi": "FastAPI",
    "fast-api": "FastAPI",
    "django": "Django",
    "drf": "Django",
    "django rest framework": "Django",
    "flask": "Flask",
    "node": "Node.js",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "express": "Node.js",
    "expressjs": "Node.js",
    "golang": "Go",
    "go": "Go",
    "rust": "Rust",
    "rustlang": "Rust",
    "java": "Java",
    "spring": "Java",
    "spring boot": "Java",
    "c#": "C#",
    "csharp": "C#",
    ".net": "C#",
    "dotnet": "C#",
    "asp.net": "C#",
    "c++": "C++",
    "cpp": "C++",
    "php": "PHP",
    "laravel": "PHP",
    "wordpress": "PHP",
    "ruby": "Ruby",
    "rails": "Ruby",
    "ruby on rails": "Ruby",
    # Frontend
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "es6": "JavaScript",
    "react": "React",
    "reactjs": "React",
    "react.js": "React",
    "next": "Next.js",
    "nextjs": "Next.js",
    "next.js": "Next.js",
    "vue": "Vue",
    "vuejs": "Vue",
    "vue.js": "Vue",
    "nuxt": "Vue",
    "angular": "Angular",
    "svelte": "Svelte",
    "sveltekit": "Svelte",
    "tailwind": "TailwindCSS",
    "tailwindcss": "TailwindCSS",
    "graphql": "GraphQL",
    "html": "HTML/CSS",
    "css": "HTML/CSS",
    "html5": "HTML/CSS",
    "css3": "HTML/CSS",
    # Databases & Caching
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "psql": "PostgreSQL",
    "mysql": "MySQL",
    "mariadb": "MySQL",
    "mongodb": "MongoDB",
    "mongo": "MongoDB",
    "redis": "Redis",
    "sqlite": "SQLite",
    "sql": "SQL",
    "snowflake": "Snowflake",
    "bigquery": "BigQuery",
    # Cloud, DevOps & Infra
    "docker": "Docker",
    "container": "Docker",
    "containers": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "aws": "AWS",
    "amazon web services": "AWS",
    "gcp": "GCP",
    "google cloud": "GCP",
    "azure": "Azure",
    "terraform": "Terraform",
    "ci/cd": "CI/CD",
    "cicd": "CI/CD",
    "github actions": "CI/CD",
    "linux": "Linux",
    # Scraping & Automation
    "scraping": "Web Scraping",
    "web scraping": "Web Scraping",
    "scraper": "Web Scraping",
    "crawler": "Web Scraping",
    "playwright": "Playwright",
    "selenium": "Selenium",
    "beautifulsoup": "BeautifulSoup",
    "bs4": "BeautifulSoup",
    "scrapy": "Web Scraping",
    # Mobile
    "react native": "React Native",
    "flutter": "Flutter",
    "ios": "iOS",
    "swift": "iOS",
    "android": "Android",
    "kotlin": "Android",
}

# Related skill graph: mapping specialized technology to implied foundational skills
RELATED_SKILLS_GRAPH: dict[str, list[str]] = {
    # AI & ML
    "LangChain": ["Python", "LLM", "RAG", "OpenAI"],
    "LlamaIndex": ["Python", "LLM", "RAG", "Vector Database"],
    "RAG": ["LLM", "Vector Database", "Python"],
    "OpenAI": ["LLM"],
    "Anthropic": ["LLM"],
    "Gemini": ["LLM"],
    "PyTorch": ["Python", "Machine Learning"],
    "TensorFlow": ["Python", "Machine Learning"],
    "HuggingFace": ["Python", "PyTorch", "LLM", "NLP"],
    "Fine-Tuning": ["PyTorch", "LLM", "Python"],
    # Backend Frameworks
    "FastAPI": ["Python", "SQL"],
    "Django": ["Python", "SQL", "HTML/CSS"],
    "Flask": ["Python"],
    "Node.js": ["JavaScript", "TypeScript"],
    # Frontend Frameworks
    "Next.js": ["React", "TypeScript", "JavaScript", "HTML/CSS"],
    "React": ["JavaScript", "TypeScript", "HTML/CSS"],
    "Vue": ["JavaScript", "HTML/CSS"],
    "Angular": ["TypeScript", "JavaScript", "HTML/CSS"],
    "Svelte": ["JavaScript", "HTML/CSS"],
    # Scraping & Automation
    "Playwright": ["Web Scraping", "Python", "TypeScript", "JavaScript"],
    "Selenium": ["Web Scraping", "Python"],
    "BeautifulSoup": ["Web Scraping", "Python", "HTML/CSS"],
    # Mobile
    "React Native": ["React", "JavaScript", "TypeScript"],
    "Flutter": ["Dart"],
    # Databases
    "PostgreSQL": ["SQL"],
    "MySQL": ["SQL"],
    "SQLite": ["SQL"],
}


def normalize_skill_name(skill: str) -> str:
    """
    Map raw skill name or synonym alias to canonical name.
    If no synonym match, returns cleaned string.
    """
    clean = skill.strip().lower()
    return SYNONYM_MAP.get(clean, skill.strip())


def get_implied_skills(skill: str) -> list[str]:
    """
    Retrieve implied foundational and related skills for a given canonical technology.
    """
    canonical = normalize_skill_name(skill)
    return RELATED_SKILLS_GRAPH.get(canonical, [])
