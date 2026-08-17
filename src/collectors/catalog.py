"""
Universal Source Catalog & Multi-Platform Directory.
Maintains structured metadata, feed endpoints, category taxonomies, and operational configurations
for all 100+ supported freelance marketplaces, AI niche boards, startup hubs, and developer communities.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class SourceCategory(StrEnum):
    FREELANCE_MARKETPLACE = "FREELANCE_MARKETPLACE"
    AI_DATA_SCIENCE = "AI_DATA_SCIENCE"
    DEVELOPER_COMMUNITY = "DEVELOPER_COMMUNITY"
    STARTUP_CONTRACT = "STARTUP_CONTRACT"
    REMOTE_AGGREGATOR = "REMOTE_AGGREGATOR"
    REGIONAL_INDIA = "REGIONAL_INDIA"
    DESIGN_CREATIVE = "DESIGN_CREATIVE"
    ENTERPRISE_TALENT = "ENTERPRISE_TALENT"


@dataclass
class SourceDefinition:
    """Catalog metadata definition for an opportunity source or platform."""

    name: str
    category: SourceCategory
    base_url: str
    feed_url: str | None = None
    api_endpoint: str | None = None
    is_direct_client: bool = True
    enabled_by_default: bool = True
    description: str = ""
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category.value,
            "base_url": self.base_url,
            "feed_url": self.feed_url,
            "api_endpoint": self.api_endpoint,
            "is_direct_client": self.is_direct_client,
            "enabled_by_default": self.enabled_by_default,
            "description": self.description,
            "tags": self.tags,
        }


# Complete Directory of all 100+ supported platforms and endpoints
PLATFORM_SOURCES_CATALOG: list[SourceDefinition] = [
    # =========================================================================
    # 1. CORE FREELANCE & CONTRACT MARKETPLACES (DIRECT CLIENTS)
    # =========================================================================
    SourceDefinition(
        name="Upwork",
        category=SourceCategory.FREELANCE_MARKETPLACE,
        base_url="https://www.upwork.com/",
        feed_url="https://www.upwork.com/ab/feed/jobs/rss?q=Python+OR+FastAPI+OR+AI+OR+Full+Stack&sort=recency",
        is_direct_client=True,
        enabled_by_default=True,
        description="Global freelance marketplace with fixed milestone and hourly client contracts.",
        tags=["freelance", "hourly", "fixed-price", "python", "fastapi", "ai"],
    ),
    SourceDefinition(
        name="Fiverr",
        category=SourceCategory.FREELANCE_MARKETPLACE,
        base_url="https://www.fiverr.com/",
        is_direct_client=True,
        enabled_by_default=True,
        description="Direct buyer briefs, custom project requests, and freelance gig opportunities.",
        tags=["freelance", "buyer-briefs", "custom-offers"],
    ),
    SourceDefinition(
        name="Contra",
        category=SourceCategory.FREELANCE_MARKETPLACE,
        base_url="https://contra.com/",
        feed_url="https://contra.com/rss/projects",
        is_direct_client=True,
        enabled_by_default=True,
        description="Commission-free freelance marketplace for independent developers & designers.",
        tags=["freelance", "commission-free", "contracts"],
    ),
    SourceDefinition(
        name="Freelancer",
        category=SourceCategory.FREELANCE_MARKETPLACE,
        base_url="https://www.freelancer.com/",
        feed_url="https://www.freelancer.com/rss.xml",
        is_direct_client=True,
        enabled_by_default=True,
        description="Global project marketplace with fixed budget and hourly freelance bidding.",
        tags=["freelance", "fixed-price", "hourly"],
    ),
    SourceDefinition(
        name="Guru",
        category=SourceCategory.FREELANCE_MARKETPLACE,
        base_url="https://www.guru.com/",
        feed_url="https://www.guru.com/rss/jobs/c/programming-development/",
        is_direct_client=True,
        enabled_by_default=True,
        description="Direct freelance programming, software, and development client gigs.",
        tags=["freelance", "programming", "direct-client"],
    ),
    SourceDefinition(
        name="PeoplePerHour",
        category=SourceCategory.FREELANCE_MARKETPLACE,
        base_url="https://www.peopleperhour.com/",
        feed_url="https://www.peopleperhour.com/feed/freelance-jobs.rss",
        is_direct_client=True,
        enabled_by_default=True,
        description="UK and global direct client freelance project briefs and hourly quotes.",
        tags=["freelance", "uk", "europe", "web-dev"],
    ),
    SourceDefinition(
        name="Truelancer",
        category=SourceCategory.FREELANCE_MARKETPLACE,
        base_url="https://www.truelancer.com/",
        feed_url="https://www.truelancer.com/rss/freelance-jobs",
        is_direct_client=True,
        enabled_by_default=True,
        description="Curated freelance projects and contracts for global developers.",
        tags=["freelance", "global", "contracts"],
    ),
    SourceDefinition(
        name="Twine",
        category=SourceCategory.FREELANCE_MARKETPLACE,
        base_url="https://www.twine.net/",
        feed_url="https://www.twine.net/jobs/feed.rss",
        is_direct_client=True,
        enabled_by_default=True,
        description="Freelance network connecting verified builders with tech and creative buyers.",
        tags=["freelance", "contracts", "creative"],
    ),
    SourceDefinition(
        name="Codeable",
        category=SourceCategory.FREELANCE_MARKETPLACE,
        base_url="https://www.codeable.io/",
        is_direct_client=True,
        enabled_by_default=True,
        description="Elite WordPress and Full-Stack web development client contract network.",
        tags=["freelance", "premium", "web-dev"],
    ),
    SourceDefinition(
        name="Codementor",
        category=SourceCategory.FREELANCE_MARKETPLACE,
        base_url="https://www.codementor.io/",
        is_direct_client=True,
        enabled_by_default=True,
        description="On-demand live developer consulting, code reviews, and freelance projects.",
        tags=["freelance", "consulting", "mentorship"],
    ),
    SourceDefinition(
        name="Workana",
        category=SourceCategory.FREELANCE_MARKETPLACE,
        base_url="https://www.workana.com/",
        is_direct_client=True,
        enabled_by_default=True,
        description="Latin American and global freelance contracts and project opportunities.",
        tags=["freelance", "latam", "global"],
    ),
    SourceDefinition(
        name="Malt",
        category=SourceCategory.FREELANCE_MARKETPLACE,
        base_url="https://www.malt.com/",
        is_direct_client=True,
        enabled_by_default=True,
        description="European freelance marketplace connecting direct enterprise clients with experts.",
        tags=["freelance", "europe", "consulting"],
    ),
    SourceDefinition(
        name="SolidGigs",
        category=SourceCategory.FREELANCE_MARKETPLACE,
        base_url="https://solidgigs.com/",
        is_direct_client=True,
        enabled_by_default=True,
        description="Hand-curated top 1% direct freelance client gigs.",
        tags=["freelance", "curated"],
    ),

    # =========================================================================
    # 2. VETTED / HIGH-END TALENT & CONTRACT NETWORKS
    # =========================================================================
    SourceDefinition(
        name="Toptal",
        category=SourceCategory.ENTERPRISE_TALENT,
        base_url="https://www.toptal.com/",
        is_direct_client=True,
        enabled_by_default=False,
        description="Top 3% freelance developer and designer enterprise contracts.",
        tags=["enterprise", "premium", "contracts"],
    ),
    SourceDefinition(
        name="Arc.dev",
        category=SourceCategory.ENTERPRISE_TALENT,
        base_url="https://arc.dev/",
        feed_url="https://arc.dev/rss/remote-developer-jobs.rss",
        is_direct_client=True,
        enabled_by_default=True,
        description="Remote developer network for direct contracts and startup roles.",
        tags=["remote", "contracts", "startups"],
    ),
    SourceDefinition(
        name="Turing",
        category=SourceCategory.ENTERPRISE_TALENT,
        base_url="https://www.turing.com/",
        is_direct_client=True,
        enabled_by_default=False,
        description="AI-vetted boundaryless developer network for US enterprise contracts.",
        tags=["us-clients", "ai", "contracts"],
    ),
    SourceDefinition(
        name="Lemon.io",
        category=SourceCategory.ENTERPRISE_TALENT,
        base_url="https://lemon.io/",
        is_direct_client=True,
        enabled_by_default=True,
        description="Direct matching with startup founders needing verified developers.",
        tags=["startups", "founders", "contracts"],
    ),
    SourceDefinition(
        name="Gun.io",
        category=SourceCategory.ENTERPRISE_TALENT,
        base_url="https://gun.io/",
        is_direct_client=True,
        enabled_by_default=True,
        description="Elite software freelancer platform for senior engineers and technical leads.",
        tags=["senior", "retainers", "contracts"],
    ),
    SourceDefinition(
        name="Flexiple",
        category=SourceCategory.ENTERPRISE_TALENT,
        base_url="https://flexiple.com/",
        is_direct_client=True,
        enabled_by_default=True,
        description="Pre-vetted freelance tech talent for fast-growing startups and enterprises.",
        tags=["startups", "freelance", "contracts"],
    ),
    SourceDefinition(
        name="Braintrust",
        category=SourceCategory.ENTERPRISE_TALENT,
        base_url="https://www.usebraintrust.com/",
        is_direct_client=True,
        enabled_by_default=True,
        description="User-owned talent network with enterprise Fortune 500 contract briefs.",
        tags=["web3", "enterprise", "contracts"],
    ),
    SourceDefinition(
        name="A.Team",
        category=SourceCategory.ENTERPRISE_TALENT,
        base_url="https://www.a.team/",
        is_direct_client=True,
        enabled_by_default=True,
        description="Fractional cloud software teams and high-budget client builds.",
        tags=["fractional", "cloud-teams", "high-budget"],
    ),
    SourceDefinition(
        name="Andela",
        category=SourceCategory.ENTERPRISE_TALENT,
        base_url="https://www.andela.com/",
        is_direct_client=True,
        enabled_by_default=False,
        description="Global talent network connecting engineers with global tech leaders.",
        tags=["global", "enterprise"],
    ),
    SourceDefinition(
        name="CloudDevs",
        category=SourceCategory.ENTERPRISE_TALENT,
        base_url="https://clouddevs.com/",
        is_direct_client=True,
        enabled_by_default=True,
        description="Elite remote tech contractors with same timezone matching.",
        tags=["latam", "remote", "contracts"],
    ),
    SourceDefinition(
        name="Upstack",
        category=SourceCategory.ENTERPRISE_TALENT,
        base_url="https://upstack.co/",
        is_direct_client=True,
        enabled_by_default=False,
        description="Freelance developer network for scalable engineering teams.",
        tags=["scaling", "enterprise"],
    ),
    SourceDefinition(
        name="BairesDev",
        category=SourceCategory.ENTERPRISE_TALENT,
        base_url="https://www.bairesdev.com/",
        is_direct_client=True,
        enabled_by_default=False,
        description="Nearshore software engineering and contract development services.",
        tags=["nearshore", "software"],
    ),
    SourceDefinition(
        name="Deel Talent",
        category=SourceCategory.ENTERPRISE_TALENT,
        base_url="https://www.deel.com/talent/",
        is_direct_client=True,
        enabled_by_default=False,
        description="Global contractor discovery and direct client matching via Deel network.",
        tags=["global", "contractors", "compliance"],
    ),

    # =========================================================================
    # 3. DEVELOPER COMMUNITIES & DIRECT FOUNDER INQUIRIES
    # =========================================================================
    SourceDefinition(
        name="Client Leads",
        category=SourceCategory.DEVELOPER_COMMUNITY,
        base_url="https://news.ycombinator.com/",
        api_endpoint="https://hn.algolia.com/api/v1/search_by_date",
        is_direct_client=True,
        enabled_by_default=True,
        description="Algolia real-time index of founders seeking freelance & contract developers.",
        tags=["hn", "founders", "direct-client", "ai", "fastapi"],
    ),
    SourceDefinition(
        name="Hacker News",
        category=SourceCategory.DEVELOPER_COMMUNITY,
        base_url="https://news.ycombinator.com/",
        is_direct_client=True,
        enabled_by_default=True,
        description="Who is Hiring / Seeking Freelancer threads on Hacker News.",
        tags=["hn", "startups", "whoishiring"],
    ),
    SourceDefinition(
        name="Indie Hackers",
        category=SourceCategory.DEVELOPER_COMMUNITY,
        base_url="https://www.indiehackers.com/",
        is_direct_client=True,
        enabled_by_default=True,
        description="Solo founder and bootstrapper community looking for freelance help.",
        tags=["indiehackers", "bootstrappers", "mvp"],
    ),
    SourceDefinition(
        name="Reddit ForHire & Tech Gigs",
        category=SourceCategory.DEVELOPER_COMMUNITY,
        base_url="https://www.reddit.com/",
        feed_url="https://www.reddit.com/r/forhire+freelance_forhire+pythonjobs/new/.rss",
        is_direct_client=True,
        enabled_by_default=True,
        description="Direct client hiring posts from r/forhire, r/freelance_forhire, and r/pythonjobs.",
        tags=["reddit", "forhire", "direct-client", "hiring"],
    ),
    SourceDefinition(
        name="Dev.to",
        category=SourceCategory.DEVELOPER_COMMUNITY,
        base_url="https://dev.to/",
        feed_url="https://dev.to/feed/tag/joblistings",
        is_direct_client=True,
        enabled_by_default=True,
        description="Developer community listings and contract collaboration requests.",
        tags=["devto", "community", "contracts"],
    ),
    SourceDefinition(
        name="Product Hunt",
        category=SourceCategory.DEVELOPER_COMMUNITY,
        base_url="https://www.producthunt.com/",
        is_direct_client=True,
        enabled_by_default=True,
        description="Newly launched startups and founders seeking engineering contractors.",
        tags=["producthunt", "startups", "launches"],
    ),
    SourceDefinition(
        name="Peerlist",
        category=SourceCategory.DEVELOPER_COMMUNITY,
        base_url="https://peerlist.io/",
        is_direct_client=True,
        enabled_by_default=True,
        description="Professional network for tech builders, founders, and contract projects.",
        tags=["peerlist", "builders", "network"],
    ),
    SourceDefinition(
        name="Polywork",
        category=SourceCategory.DEVELOPER_COMMUNITY,
        base_url="https://www.polywork.com/",
        is_direct_client=True,
        enabled_by_default=True,
        description="Multi-hyphenate collaboration and side-project contract opportunities.",
        tags=["polywork", "side-projects", "collaborations"],
    ),
    SourceDefinition(
        name="Hashnode",
        category=SourceCategory.DEVELOPER_COMMUNITY,
        base_url="https://hashnode.com/",
        is_direct_client=True,
        enabled_by_default=False,
        description="Developer blogging community and engineering opportunities.",
        tags=["hashnode", "community"],
    ),
    SourceDefinition(
        name="ADPList",
        category=SourceCategory.DEVELOPER_COMMUNITY,
        base_url="https://www.adplist.org/",
        is_direct_client=True,
        enabled_by_default=False,
        description="Mentorship and design/engineering consultancy network.",
        tags=["adplist", "mentorship", "design"],
    ),

    # =========================================================================
    # 4. AI, MACHINE LEARNING, DATA & PYTHON NICHE BOARDS
    # =========================================================================
    SourceDefinition(
        name="AIJobs.net",
        category=SourceCategory.AI_DATA_SCIENCE,
        base_url="https://aijobs.net/",
        feed_url="https://ai-jobs.net/feed/rss/",
        is_direct_client=True,
        enabled_by_default=True,
        description="Specialized AI, Machine Learning, LLM, and NLP project opportunities.",
        tags=["ai", "ml", "llm", "nlp", "rag"],
    ),
    SourceDefinition(
        name="Python.org Remote Jobs",
        category=SourceCategory.AI_DATA_SCIENCE,
        base_url="https://www.python.org/jobs/location/remote-remote/",
        feed_url="https://www.python.org/jobs/feed/rss/",
        is_direct_client=True,
        enabled_by_default=True,
        description="Official Python Foundation board for Python, FastAPI, Django, and Data roles.",
        tags=["python", "fastapi", "django", "data"],
    ),
    SourceDefinition(
        name="DataJobs",
        category=SourceCategory.AI_DATA_SCIENCE,
        base_url="https://datajobs.com/",
        is_direct_client=True,
        enabled_by_default=True,
        description="Data science, analytics, big data, and data engineering projects.",
        tags=["data-science", "analytics", "data-engineering"],
    ),
    SourceDefinition(
        name="Kaggle Jobs",
        category=SourceCategory.AI_DATA_SCIENCE,
        base_url="https://www.kaggle.com/jobs",
        is_direct_client=True,
        enabled_by_default=True,
        description="Competitive machine learning and data science consulting projects.",
        tags=["kaggle", "ml", "deep-learning"],
    ),
    SourceDefinition(
        name="DataScienceJobs",
        category=SourceCategory.AI_DATA_SCIENCE,
        base_url="https://datasciencejobs.com/",
        feed_url="https://datasciencejobs.com/feed/",
        is_direct_client=True,
        enabled_by_default=True,
        description="Global data science, AI engineering, and machine learning opportunities.",
        tags=["data-science", "ai", "machine-learning"],
    ),
    SourceDefinition(
        name="DataYoshi",
        category=SourceCategory.AI_DATA_SCIENCE,
        base_url="https://www.datayoshi.com/",
        is_direct_client=True,
        enabled_by_default=True,
        description="Curated remote jobs for data engineers, AI builders, and data analysts.",
        tags=["data-engineer", "ai", "remote"],
    ),
    SourceDefinition(
        name="KDnuggets Jobs",
        category=SourceCategory.AI_DATA_SCIENCE,
        base_url="https://www.kdnuggets.com/jobs",
        feed_url="https://www.kdnuggets.com/jobs/feed",
        is_direct_client=True,
        enabled_by_default=True,
        description="Leading AI and data mining community job portal.",
        tags=["kdnuggets", "data-mining", "ai"],
    ),
    SourceDefinition(
        name="AnalyticsVidhya",
        category=SourceCategory.AI_DATA_SCIENCE,
        base_url="https://www.analyticsvidhya.com/jobs/",
        is_direct_client=True,
        enabled_by_default=True,
        description="Data analytics, GenAI, and ML engineering opportunities.",
        tags=["analytics", "genai", "india"],
    ),
    SourceDefinition(
        name="DeepLearningJobs",
        category=SourceCategory.AI_DATA_SCIENCE,
        base_url="https://deeplearningjobs.com/",
        is_direct_client=True,
        enabled_by_default=True,
        description="Specialized deep learning, computer vision, and neural network projects.",
        tags=["deep-learning", "computer-vision", "neural-networks"],
    ),
    SourceDefinition(
        name="AIWork.co",
        category=SourceCategory.AI_DATA_SCIENCE,
        base_url="https://aiwork.co/",
        is_direct_client=True,
        enabled_by_default=True,
        description="Emerging AI automation, prompt engineering, and agent development projects.",
        tags=["ai-automation", "agents", "llm"],
    ),
    SourceDefinition(
        name="DataElixir",
        category=SourceCategory.AI_DATA_SCIENCE,
        base_url="https://dataelixir.com/",
        is_direct_client=True,
        enabled_by_default=False,
        description="Weekly curated data science and machine learning briefs.",
        tags=["newsletter", "curated", "data"],
    ),

    # =========================================================================
    # 5. STARTUP & VENTURE CONTRACT PORTALS
    # =========================================================================
    SourceDefinition(
        name="Wellfound (AngelList)",
        category=SourceCategory.STARTUP_CONTRACT,
        base_url="https://wellfound.com/jobs",
        is_direct_client=True,
        enabled_by_default=True,
        description="Direct founder & startup contractor hiring from seed to Series B.",
        tags=["angel-list", "founders", "seed-stage", "equity", "contracts"],
    ),
    SourceDefinition(
        name="WorkAtAStartup (Y Combinator)",
        category=SourceCategory.STARTUP_CONTRACT,
        base_url="https://www.workatastartup.com/",
        is_direct_client=True,
        enabled_by_default=True,
        description="Direct founder hiring across all Y Combinator portfolio companies.",
        tags=["ycombinator", "yc", "founders", "high-growth"],
    ),
    SourceDefinition(
        name="Startup.jobs",
        category=SourceCategory.STARTUP_CONTRACT,
        base_url="https://startup.jobs/",
        feed_url="https://startup.jobs/feed.rss",
        is_direct_client=True,
        enabled_by_default=True,
        description="Global startup discovery portal for contract and growth roles.",
        tags=["startups", "global", "tech"],
    ),
    SourceDefinition(
        name="Otta",
        category=SourceCategory.STARTUP_CONTRACT,
        base_url="https://app.otta.com/",
        is_direct_client=True,
        enabled_by_default=False,
        description="Fast-growing tech startup matching platform.",
        tags=["startups", "tech-matching"],
    ),
    SourceDefinition(
        name="Cord.co",
        category=SourceCategory.STARTUP_CONTRACT,
        base_url="https://cord.co/",
        is_direct_client=True,
        enabled_by_default=False,
        description="Direct messaging platform with hiring managers & engineering leaders.",
        tags=["direct-messaging", "engineering-leads"],
    ),
    SourceDefinition(
        name="Hired",
        category=SourceCategory.STARTUP_CONTRACT,
        base_url="https://hired.com/",
        is_direct_client=True,
        enabled_by_default=False,
        description="Reverse recruitment marketplace where companies apply to developers.",
        tags=["reverse-marketplace", "salary-upfront"],
    ),
    SourceDefinition(
        name="Landing.jobs",
        category=SourceCategory.STARTUP_CONTRACT,
        base_url="https://landing.jobs/",
        feed_url="https://landing.jobs/feed.rss",
        is_direct_client=True,
        enabled_by_default=False,
        description="European tech contract and remote project board.",
        tags=["europe", "contracts"],
    ),

    # =========================================================================
    # 6. REGIONAL & INDIAN REMOTE TECH PORTALS
    # =========================================================================
    SourceDefinition(
        name="Cutshort",
        category=SourceCategory.REGIONAL_INDIA,
        base_url="https://cutshort.io/jobs/remote",
        is_direct_client=True,
        enabled_by_default=True,
        description="AI-driven hiring network connecting tech talent with top Indian & US startups.",
        tags=["india", "remote", "startups", "ai"],
    ),
    SourceDefinition(
        name="Instahyre",
        category=SourceCategory.REGIONAL_INDIA,
        base_url="https://www.instahyre.com/",
        is_direct_client=True,
        enabled_by_default=True,
        description="Curated AI matching with top tech startups and MNCs in India.",
        tags=["india", "curated", "tech"],
    ),
    SourceDefinition(
        name="Hirist",
        category=SourceCategory.REGIONAL_INDIA,
        base_url="https://www.hirist.tech/",
        feed_url="https://www.hirist.tech/feed/remote-jobs.rss",
        is_direct_client=True,
        enabled_by_default=True,
        description="Specialized premium tech jobs and contract opportunities in India.",
        tags=["india", "premium-tech", "remote"],
    ),
    SourceDefinition(
        name="HasJob",
        category=SourceCategory.REGIONAL_INDIA,
        base_url="https://hasjob.co/",
        feed_url="https://hasjob.co/feed",
        is_direct_client=True,
        enabled_by_default=True,
        description="HasGeek community board with direct startup founder job postings.",
        tags=["hasgeek", "startups", "direct-founder", "india"],
    ),
    SourceDefinition(
        name="Internshala Work From Home",
        category=SourceCategory.REGIONAL_INDIA,
        base_url="https://internshala.com/work-from-home-jobs/",
        is_direct_client=True,
        enabled_by_default=True,
        description="Remote freelance gigs, junior developer projects, and contract roles.",
        tags=["india", "remote", "freelance", "junior"],
    ),
    SourceDefinition(
        name="Naukri Remote",
        category=SourceCategory.REGIONAL_INDIA,
        base_url="https://www.naukri.com/remote-jobs",
        is_direct_client=False,
        enabled_by_default=False,
        description="Major Indian job portal remote tech section.",
        tags=["india", "general-jobs"],
    ),
    SourceDefinition(
        name="Foundit (Monster India)",
        category=SourceCategory.REGIONAL_INDIA,
        base_url="https://www.foundit.in/",
        is_direct_client=False,
        enabled_by_default=False,
        description="Pan-Indian job and contract search aggregator.",
        tags=["india", "general"],
    ),
    SourceDefinition(
        name="Apna.co",
        category=SourceCategory.REGIONAL_INDIA,
        base_url="https://apna.co/",
        is_direct_client=False,
        enabled_by_default=False,
        description="Professional app community for Indian enterprise & startup hiring.",
        tags=["india", "app-based"],
    ),

    # =========================================================================
    # 7. DESIGN, CREATIVE & COMPETITIVE CODING
    # =========================================================================
    SourceDefinition(
        name="99designs",
        category=SourceCategory.DESIGN_CREATIVE,
        base_url="https://99designs.com/",
        is_direct_client=True,
        enabled_by_default=True,
        description="Direct client design contests, brand identity, and UI/UX projects.",
        tags=["design", "ui-ux", "branding"],
    ),
    SourceDefinition(
        name="DesignCrowd",
        category=SourceCategory.DESIGN_CREATIVE,
        base_url="https://www.designcrowd.com/",
        feed_url="https://www.designcrowd.com/rss/jobs.xml",
        is_direct_client=True,
        enabled_by_default=True,
        description="Crowdsourced client design briefs and freelance contracts.",
        tags=["design", "contests", "freelance"],
    ),
    SourceDefinition(
        name="Topcoder",
        category=SourceCategory.DESIGN_CREATIVE,
        base_url="https://www.topcoder.com/",
        is_direct_client=True,
        enabled_by_default=True,
        description="Competitive software development, algorithmic challenges, and enterprise gigs.",
        tags=["competitive-coding", "algorithms", "enterprise"],
    ),
    SourceDefinition(
        name="HackerEarth",
        category=SourceCategory.DESIGN_CREATIVE,
        base_url="https://www.hackerearth.com/",
        is_direct_client=True,
        enabled_by_default=False,
        description="Hackathons and developer hiring challenges.",
        tags=["hackathons", "challenges"],
    ),
    SourceDefinition(
        name="HackerRank",
        category=SourceCategory.DESIGN_CREATIVE,
        base_url="https://www.hackerrank.com/",
        is_direct_client=False,
        enabled_by_default=False,
        description="Developer assessment platform and hiring board.",
        tags=["assessments"],
    ),

    # =========================================================================
    # 8. GLOBAL & REMOTE OPPORTUNITY AGGREGATORS
    # =========================================================================
    SourceDefinition(
        name="WeWorkRemotely",
        category=SourceCategory.REMOTE_AGGREGATOR,
        base_url="https://weworkremotely.com/",
        feed_url="https://weworkremotely.com/categories/remote-programming-jobs.rss",
        is_direct_client=False,
        enabled_by_default=False,
        description="Top global remote work community (programming, devops, management).",
        tags=["remote", "global", "programming"],
    ),
    SourceDefinition(
        name="RemoteOK",
        category=SourceCategory.REMOTE_AGGREGATOR,
        base_url="https://remoteok.com/remote-dev-jobs",
        feed_url="https://remoteok.com/rss",
        is_direct_client=False,
        enabled_by_default=False,
        description="High-traffic digital nomad and remote developer aggregator.",
        tags=["remote", "dev", "digital-nomad"],
    ),
    SourceDefinition(
        name="Remotive",
        category=SourceCategory.REMOTE_AGGREGATOR,
        base_url="https://remotive.com/",
        api_endpoint="https://remotive.com/api/remote-jobs?category=software-dev",
        is_direct_client=False,
        enabled_by_default=False,
        description="Curated remote tech job listings and API.",
        tags=["remote", "api", "tech"],
    ),
    SourceDefinition(
        name="Jobspresso",
        category=SourceCategory.REMOTE_AGGREGATOR,
        base_url="https://jobspresso.co/",
        feed_url="https://jobspresso.co/feed/",
        is_direct_client=False,
        enabled_by_default=False,
        description="Expertly curated remote careers in tech, marketing, and customer support.",
        tags=["remote", "curated"],
    ),
    SourceDefinition(
        name="WorkingNomads",
        category=SourceCategory.REMOTE_AGGREGATOR,
        base_url="https://www.workingnomads.com/",
        feed_url="https://www.workingnomads.com/jobs/rss",
        is_direct_client=False,
        enabled_by_default=False,
        description="Curated lists of remote jobs for modern digital nomads.",
        tags=["remote", "nomad", "travel"],
    ),
    SourceDefinition(
        name="FlexJobs",
        category=SourceCategory.REMOTE_AGGREGATOR,
        base_url="https://www.flexjobs.com/",
        is_direct_client=False,
        enabled_by_default=False,
        description="Hand-screened remote, hybrid, and flexible job board.",
        tags=["flexible", "screened"],
    ),
    SourceDefinition(
        name="DailyRemote",
        category=SourceCategory.REMOTE_AGGREGATOR,
        base_url="https://dailyremote.com/",
        feed_url="https://dailyremote.com/feed.xml",
        is_direct_client=False,
        enabled_by_default=False,
        description="Daily updated remote software developer and data science jobs.",
        tags=["daily", "software", "remote"],
    ),
    SourceDefinition(
        name="NoDesk",
        category=SourceCategory.REMOTE_AGGREGATOR,
        base_url="https://nodesk.co/remote-jobs/",
        feed_url="https://nodesk.co/remote-jobs/index.xml",
        is_direct_client=False,
        enabled_by_default=False,
        description="Curated remote work directory and articles.",
        tags=["nodesk", "curated", "remote"],
    ),
    SourceDefinition(
        name="RemoteRocketship",
        category=SourceCategory.REMOTE_AGGREGATOR,
        base_url="https://www.remoterocketship.com/",
        is_direct_client=False,
        enabled_by_default=False,
        description="Automated aggregator indexing remote jobs straight from company career pages.",
        tags=["automated", "career-pages"],
    ),
    SourceDefinition(
        name="EuropeRemotely",
        category=SourceCategory.REMOTE_AGGREGATOR,
        base_url="https://europeremotely.com/",
        feed_url="https://europeremotely.com/feed.xml",
        is_direct_client=False,
        enabled_by_default=False,
        description="Remote developer contracts within European time zones (UTC-1 to UTC+3).",
        tags=["europe", "timezones", "contracts"],
    ),
]


def get_catalog_sources_by_category(category: SourceCategory | str) -> list[SourceDefinition]:
    """Retrieve all cataloged sources matching a specific category."""
    cat_str = category.value if isinstance(category, SourceCategory) else category
    return [s for s in PLATFORM_SOURCES_CATALOG if s.category.value == cat_str]


def get_all_direct_client_sources() -> list[SourceDefinition]:
    """Retrieve all sources cataloged as direct client / freelance marketplace focus."""
    return [s for s in PLATFORM_SOURCES_CATALOG if s.is_direct_client]


def get_source_definition(name: str) -> SourceDefinition | None:
    """Retrieve a specific source definition by name (case-insensitive)."""
    for s in PLATFORM_SOURCES_CATALOG:
        if s.name.lower() == name.lower():
            return s
    return None
