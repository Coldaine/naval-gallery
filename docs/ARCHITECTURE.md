# Architecture

## Storage Model

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Git Repository                                 │
│  naval-gallery/                                                          │
│  ├── data/                    ← Manifests (JSON metadata)               │
│  │   ├── master_manifest.json                                           │
│  │   └── *_manifest.json                                                │
│  ├── tools/                   ← Harvesters and utilities                │
│  └── index.html               ← Frontend                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ local_path references
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Google Drive (External Storage)                       │
│  ~/GoogleDrive/NavalGallery/                                            │
│  ├── wiki/                    ← Wikimedia Commons images                │
│  ├── loc/                     ← Library of Congress                     │
│  ├── ia/                      ← Internet Archive                        │
│  ├── oni/                     ← ONI/military documents                  │
│  ├── dreadnought/             ← Dreadnought Project                     │
│  ├── blueprints/              ← NavSource                               │
│  └── pinterest/               ← Pinterest boards                        │
└─────────────────────────────────────────────────────────────────────────┘
```

### Why External Storage?

1. **Repository size**: Images would bloat git history (hundreds of MB)
2. **Cloud sync**: Google Drive syncs automatically across devices
3. **Separation of concerns**: Code in git, assets in cloud storage
4. **Portability**: Same manifests work on any machine with Google Drive mounted

### Auto-Detection

The config module (`tools/config.py`) auto-detects Google Drive:

```python
# Checked in order (relative to home directory)
GOOGLE_DRIVE_PATTERNS = [
    "GoogleDrive",           # rclone default
    "Google Drive",          # GNOME/Nautilus
    "google-drive",          # Some Linux naming
]
```

Override with: `export NAVAL_GALLERY_IMAGE_DIR="/custom/path"`

---

## Data Flow

```
[Sources]              [Harvesters]           [Data Layer]        [Frontend]
-----------            -------------          -------------       -----------
Wikimedia Commons  →   wiki_walker.py    →   wiki_manifest.json      ↓
Internet Archive   →   deep_archivist.py →   ia_manifest.json        ↓
Library of Congress →  official_channels.py → loc_manifest.json    → images.js → index.html
Dreadnought Project →  dreadnought_scraper.py → dreadnought_manifest.json
Pinterest          →   pinterest_scraper.py → pinterest_manifest.json
                                              ↓
                                         master_manifest.json
```

## Components

### Configuration (`tools/config.py`)

Central configuration that:
- Auto-detects Google Drive mount point
- Creates `NavalGallery` subfolder if needed
- Provides `get_image_dir()`, `get_staging_dir()`, `get_relative_path()`
- Fails fast with clear error if no storage configured

### Harvesters (`tools/harvesters/`)

Each harvester:
1. Validates config (fails fast if Google Drive not mounted)
2. Queries a source API or scrapes known collections
3. Applies heuristics to filter for plate-like images
4. Downloads to Google Drive (`NavalGallery/<source>/`)
5. Outputs `data/<source>_manifest.json` with relative paths

**Key heuristics**:
- `is_landscape`: width > height * 1.1
- `is_super_wide`: width > 3500px
- `is_foldout_type`: pageType in ["foldout", "plate", "map", "chart"]

### Orchestrator (`tools/run_all.py`)

1. Validates config first (before running any harvester)
2. Runs all harvesters sequentially
3. Aggregates `*_manifest.json` files into `master_manifest.json`
4. Exports to `images.js` for frontend consumption

### Frontend (`index.html`)

Single-page app with:
- **Filters**: Navy dropdown, plate-type dropdown
- **Grid**: Responsive card layout with thumbnails
- **Modal**: Full image view with metadata

Data loaded via `<script src="data/images.js">` (no build step).

---

## Manifest Schema

```json
{
  "id": "wiki_12345",
  "title": "HMS Dreadnought Profile",
  "url": "https://...",
  "local_path": "wiki/wiki_12345.jpg",
  "source": "Wikimedia Commons",
  "navy": "UK",
  "type": "profile",
  "era": "dreadnought"
}
```

Note: `local_path` is relative to the image storage root (Google Drive), not the git repository.
