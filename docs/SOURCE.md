# Supported Project Sources & Harvesters

## 1. Source Evaluation Criteria

Before onboarding a new opportunity source into `src/collectors/`, verify:

- **Public Accessibility**: Data is openly accessible without requiring proprietary authentication or paywalls.
- **Terms of Service & robots.txt**: Ingestion complies with platform terms and robotic crawling rules.
- **Rate Limits & Backoff**: Platform supports reasonable request throttling without IP degradation.
- **Data Richness**: Opportunities provide clear title, project scope/description, skills, budget or compensation indicators, and posting timestamps.
- **Stability**: API endpoints or RSS feeds maintain predictable schema structures.

---

## 2. Active Supported Harvesters

| Source Name | Platform Type | Ingestion Method | Target Feed / URL | Operational Status |
| :--- | :--- | :--- | :--- | :--- |
| **Hacker News** | Developer Community | Algolia REST API | `hn.algolia.com/api/v1/search` (Ask HN: Freelancer threads) | `Production` |
| **RemoteOK** | Remote Job Board | REST JSON API | `remoteok.com/api` (Filtered for developer tags) | `Production` |
| **WeWorkRemotely**| Remote Job Board | RSS 2.0 XML Feed | `weworkremotely.com/categories/remote-programming-jobs.rss` | `Production` |
| **Generic RSS / Atom**| Configurable Feeds | RSS 2.0 & Atom XML | Customizable Feed URLs | `Production` |

---

## 3. Collector Details

### 3.1 Hacker News (`HackerNewsCollector`)
- **Method**: Queries Algolia Search API for monthly "Ask HN: Freelancer? Seeking Freelancer?" and "Who is hiring?" threads.
- **Processing**: Parses nested comments, isolates hiring posts from candidate availability posts, extracts contact emails and project requirements.
- **Circuit Breaker**: Monitored via `CollectorRegistry`.

### 3.2 RemoteOK (`RemoteOKCollector`)
- **Method**: Fetches structured JSON job listings directly from the RemoteOK public API.
- **Processing**: Strips HTML tags, parses salary minimums and maximums, normalizes tags to canonical skills, and identifies remote contract opportunities.

### 3.3 WeWorkRemotely (`WeWorkRemotelyCollector`)
- **Method**: Periodically parses the programming jobs RSS 2.0 feed using XML ElementTree.
- **Processing**: Extracts company name from `Company: Title` headers, parses RFC 2822 publication dates to ISO-8601 UTC timestamps, and extracts full opportunity text.

### 3.4 Configurable RSS / Atom (`RSSFeedCollector`)
- **Method**: Universal XML feed harvester supporting RSS 2.0 `<channel><item>` and Atom `<feed><entry>` schemas.
- **Processing**: Safe namespace resolution (`{http://www.w3.org/2005/Atom}`) and CDATA content extraction.