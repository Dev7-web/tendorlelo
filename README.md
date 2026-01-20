# Tender Matching System

End-to-end system for scraping GeM tenders, extracting metadata with Gemini, and matching against company profiles using hybrid search.

## Features
- GeM bid scraping with Playwright
- PDF extraction via PyMuPDF
- LLM metadata extraction (Gemini)
- Embedding-based matching (bge-small)
- FastAPI REST API
- APScheduler background jobs

## Setup

```bash
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
playwright install chromium
```

## Configure

```bash
copy .env.example .env
# Update GEMINI_API_KEY and other settings
```

## Initialize Database

```bash
python scripts/init_db.py
```

## Run API

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Run Scraper Manually

```bash
python scripts/run_scraper.py --max-pages 2 --max-bids 10
```

## API Endpoints
- `GET /health`
- `GET /api/v1/tenders/`
- `GET /api/v1/tenders/{tender_id}`
- `GET /api/v1/tenders/stats/summary`
- `POST /api/v1/companies/upload`
- `GET /api/v1/companies/{company_id}`
- `DELETE /api/v1/companies/{company_id}`
- `GET /api/v1/search/tenders/{company_id}`
