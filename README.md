# Naval Gallery

Curated collection of public-domain warship drawings—hull lines, profiles, sections, and machinery plates from pre-dreadnought through mid-20th century vessels.

## Goals

1. **Harvest** warship technical drawings from public-domain digital archives (Internet Archive, Library of Congress, Wikimedia Commons)
2. **Curate** results via manual review to filter noise from automated scraping
3. **Display** approved images in a filterable web gallery with metadata

## Storage Architecture

> **Images are stored externally in Google Drive**, not in this git repository.

This keeps the repository lightweight while images sync automatically across devices via Google Drive. The config auto-detects common mount points:

| Mount Pattern | Common Setup |
|---------------|--------------|
| `~/GoogleDrive/` | rclone |
| `~/Google Drive/` | GNOME/Nautilus |

Images are stored in `<GoogleDrive>/NavalGallery/<source>/` (e.g., `NavalGallery/wiki/`, `NavalGallery/loc/`).

**Manual override**: Set `NAVAL_GALLERY_IMAGE_DIR` environment variable to use a custom path.

## Quick Start

```bash
# 1. Ensure Google Drive is mounted (or set NAVAL_GALLERY_IMAGE_DIR)

# 2. Install dependencies
uv sync

# 3. Run all harvesters
uv run python tools/run_all.py

# 4. Serve gallery
python -m http.server 8000
# → http://localhost:8000
```

## Current State

- **Harvesters**: 7 source-specific Python scripts in `tools/harvesters/`
- **Frontend**: Single-page HTML gallery with filtering by navy/plate-type
- **Data**: JSON manifests in `data/` (committed to git)
- **Images**: External storage in Google Drive (auto-detected)

## Documentation

| Doc | Purpose |
|-----|---------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design and data flow |
| [DECISIONS.md](docs/DECISIONS.md) | Technical decisions and rationale |
