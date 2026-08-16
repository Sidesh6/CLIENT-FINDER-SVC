# CLIENT FINDER SVC — Direct Freelance Client Acquisition

Follow these steps to find direct paying freelance clients, extract founder contacts, generate winning pitches, and manage your pipeline.

---

## Step 1: Start the Web Dashboard Server

Start the FastAPI application:

```bash
uvicorn src.api.main:app --reload --port 8000
```

- **Web Dashboard**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Swagger API Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## Step 2: Fetch Live Freelance Clients from Online Sources

Run an immediate harvest cycle from live online feeds (Hacker News "Seeking Freelancer", Client Leads, etc.):

```bash
python -m src.cli harvest --limit 10
```

---

## Step 3: View Filtered Direct Freelance Clients

View direct founders, product owners, and hourly contracts (strictly excluding employee jobs):

```bash
python -m src.cli freelance-clients --limit 10
```

**Output includes:**
- Client Decision Maker Type (`DIRECT_FOUNDER`, `STARTUP_EXEC`, `PRODUCT_OWNER`)
- Engagement Model (`FIXED_MILESTONE`, `HOURLY_CONTRACT`, `MONTHLY_RETAINER`)
- Direct Reach-out Channel (`Email: founder@domain.com`, `Calendly`, `Telegram`)
- Match Score & Budget

---

## Step 4: Generate a High-Converting Freelance Pitch

Generate a customized proposal for any project ID (e.g. project ID 1):

### Option A: Direct Founder Pitch (Fast 3-paragraph outreach)
```bash
python -m src.cli pitch --project-id 1 --angle DIRECT_FOUNDER_PITCH
```

### Option B: Fixed-Price Milestone Scope Quote
```bash
python -m src.cli pitch --project-id 1 --angle FIXED_MILESTONE_QUOTE
```

### Option C: Fractional Technical Lead / Retainer Pitch
```bash
python -m src.cli pitch --project-id 1 --angle FRACTIONAL_ADVISOR
```

---

## Step 5: Run the Continuous Background Daemon (Optional)

To automatically monitor feeds 24/7 and alert you on high-scoring freelance gigs:

```bash
python -m src.cli daemon --interval 15 --min-score 75
```

---

## Step 6: Run Verification Tests

Run the full automated test suite to ensure all collectors and classifiers are working:

```bash
pytest tests/unit/test_freelance_system.py
```
