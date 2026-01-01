# Architecture

## Data Flow

```
[Sources]              [Harvesters]           [Data Layer]        [Frontend]
-----------            -------------          -------------       -----------
Wikimedia Commons  →   wiki_walker.py    →   wiki_manifest.json      ↓
Internet Archive   →   deep_archivist.py →   ia_manifest.json        ↓
Library of Congress →  official_channels.py → loc_manifest.json    → images.js → index.html
ONI/Military Docs  →   blueprints_crawler.py → oni_manifest.json     ↑
Manual URLs        →   manual_siphon.py  →   blueprints_manifest.json ↑
                                              ↓
                                         master_manifest.json
```

## Components

### Harvesters (`tools/harvesters/`)

Each harvester:
1. Queries a source API or scrapes known collections
2. Applies heuristics to filter for plate-like images (landscape orientation, large dimensions, keywords in title)
3. Downloads candidates to `img/<source>/`
4. Outputs `data/<source>_manifest.json`

**Key heuristics** (from `smart_harvester.py`):
- `is_landscape`: width > height * 1.1
- `is_super_wide`: width > 3500px
- `is_foldout_type`: pageType in ["foldout", "plate", "map", "chart"]

### Orchestrator (`tools/run_all.py`)

1. Runs all harvesters sequentially
2. Aggregates `*_manifest.json` files into `master_manifest.json`
3. Exports to `images.js` for frontend consumption

### Frontend (`index.html`)

Single-page app with:
- **Filters**: Navy dropdown, plate-type dropdown
- **Grid**: Responsive card layout with thumbnails
- **Modal**: Full image view with metadata (ship, navy, source, link)

Data loaded via `<script src="data/images.js">` (no build step).

## File Organization

```
naval-gallery/
├── index.html              # Gallery frontend
├── data/
│   ├── images.js           # JS array consumed by frontend
│   ├── master_manifest.json # Aggregated metadata
│   └── *_manifest.json     # Per-source manifests
├── img/
│   ├── wiki/               # Wikimedia Commons images
│   ├── loc/                # Library of Congress
│   ├── oni/                # ONI/military documents
│   ├── ia/                 # Internet Archive
│   └── blueprints/         # Manual additions
└── tools/
    ├── run_all.py          # Orchestrator
    ├── smart_harvester.py  # IA-focused heuristic harvester
    └── harvesters/         # Source-specific scripts
```
