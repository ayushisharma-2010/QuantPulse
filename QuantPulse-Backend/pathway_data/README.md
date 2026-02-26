# Pathway Data Directory

This directory contains data sources for the Pathway streaming pipeline.

## Directory Structure

```
pathway_data/
├── news/           # News articles (JSON files)
├── esg/            # ESG/sustainability reports (PDF, TXT, JSON)
├── models/         # Saved models and embeddings
└── README.md       # This file
```

## Usage

### News Directory (`news/`)
Drop JSON news files here. Pathway will automatically detect and index them.

**Expected JSON format:**
```json
{
  "title": "Article title",
  "content": "Article content...",
  "source": "News source",
  "published_date": "2024-01-15T10:30:00Z",
  "symbols": ["RELIANCE.NS", "TCS.NS"],
  "url": "https://example.com/article"
}
```

### ESG Directory (`esg/`)
Drop ESG/sustainability reports here. Supported formats: PDF, TXT, JSON.

**Expected JSON format:**
```json
{
  "symbol": "RELIANCE.NS",
  "company_name": "Reliance Industries",
  "report_date": "2024-01-01",
  "carbon_emissions": 85.5,
  "water_usage": 72.3,
  "board_diversity": 65.0,
  "governance_score": 78.5,
  "overall_score": 75.3,
  "category": "medium"
}
```

### Models Directory (`models/`)
Stores cached embeddings and model artifacts for faster startup.

## Data Seeding

Use the provided scripts to populate data:

```bash
# Seed news articles
python pathway_data/seed_news.py

# Seed ESG data
python pathway_data/seed_esg.py
```

## Notes

- Pathway watches these directories for changes in real-time
- New files are automatically indexed within 30 seconds
- Deleted files are automatically removed from the index
- File names should be unique to avoid conflicts
