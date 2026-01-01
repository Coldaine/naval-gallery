# Naval Gallery

Curated collection of public-domain warship drawings—hull lines, profiles, sections, and machinery plates from pre-dreadnought through mid-20th century vessels.

## Goals

1. **Harvest** warship technical drawings from public-domain digital archives (Internet Archive, Library of Congress, Wikimedia Commons)
2. **Curate** results via manual review to filter noise from automated scraping
3. **Display** approved images in a filterable web gallery with metadata

## Current State

- **Harvesters**: 5 source-specific Python scripts in `tools/harvesters/`, plus orchestrator
- **Frontend**: Single-page HTML gallery with filtering by navy/plate-type
- **Data**: JSON manifests per source, aggregated to `data/images.js`
- **Assets**: Downloaded images in `img/` organized by source

## Quick Start

```bash
# Run all harvesters
python tools/run_all.py

# Serve gallery
python -m http.server 8000
# → http://localhost:8000
```

## Documentation

| Doc | Purpose |
|-----|---------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design and data flow |
| [DECISIONS.md](docs/DECISIONS.md) | Technical decisions and rationale |
