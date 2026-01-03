# Technical Decisions

## ADR-001: Automated Harvesting with Manual Curation

**Context**: Need hundreds of warship images. Manual collection is slow. Automated scraping returns noise.

**Decision**: Hybrid approach—automated harvesters for discovery, manual review for quality control.

**Rationale**:
- Harvesters use heuristics (landscape orientation, keywords, dimensions) but these are imperfect
- Example failures: "The pie rat ship", cruise ferry deck plans, welders making boilers
- Human review catches these before images enter the curated gallery

**Consequence**: Images go to staging first; only reviewed images should move to production manifests.

---

## ADR-002: Source-Specific Harvesters

**Context**: Each archive has different APIs, rate limits, and metadata structures.

**Decision**: One harvester per source rather than one generic scraper.

**Rationale**:
- Wikimedia uses MediaWiki API with category traversal
- Internet Archive uses `internetarchive` Python library + scandata.xml parsing
- Library of Congress has unique JSON API
- Each source's metadata maps differently to our schema

**Sources implemented**:
| Harvester | Source | API |
|-----------|--------|-----|
| `wiki_walker.py` | Wikimedia Commons | MediaWiki API |
| `deep_archivist.py` | Internet Archive | IA Python lib + scandata.xml |
| `official_channels.py` | Library of Congress | LOC JSON API |
| `blueprints_crawler.py` | ONI military docs | IA with specific collection IDs |
| `manual_siphon.py` | Manual URLs | URL list + direct download |

---

## ADR-003: Simple Frontend (No Build Step)

**Context**: Need a way to view and filter collected images.

**Decision**: Single HTML file with inline CSS/JS, loading data as JS file.

**Rationale**:
- Zero dependencies, works with `python -m http.server`
- Easy to iterate without build tooling
- Good enough for personal/dev use
- Can upgrade to React/Vite if gallery grows significantly

---

## ADR-004: Manifest-Based Data Model

**Context**: Need to track image metadata and local paths.

**Decision**: JSON manifests per source, aggregated to `master_manifest.json`, exported to `images.js`.

**Schema**:
```json
{
  "id": "wiki_12345",
  "title": "HMS Dreadnought Profile",
  "url": "https://...",
  "local_path": "img/wiki/wiki_12345.jpg",
  "source": "Wikimedia Commons",
  "navy": "UK",
  "type": "profile",
  "era": "dreadnought"
}
```

**Rationale**:
- Separate manifests allow re-running individual harvesters
- Aggregation step can apply filtering/deduplication
- JS export avoids CORS issues for local development

---

## ADR-005: Era/Type Classification

**Context**: Want to filter images by era (pre-dreadnought, dreadnought, interwar, WWII) and type (profile, lines, deck, section, machinery).

**Decision**: Manual classification during curation; harvesters set defaults to "Unknown".

**Rationale**:
- Automated classification would require ML (overkill for current scale)
- Metadata from sources rarely includes era/type in consistent format
- Human can classify during review pass

---

## ADR-006: External Image Storage (Google Drive)

**Context**: Images would bloat the git repository (hundreds of MB). Need a way to store images that syncs across devices.

**Decision**: Store images externally in Google Drive, with auto-detection of mount points.

**Implementation**:
- Config module (`tools/config.py`) auto-detects `~/GoogleDrive/`, `~/Google Drive/`, etc.
- Creates `NavalGallery/` subfolder automatically
- Manifests in git reference images via relative paths (`wiki/wiki_12345.jpg`)
- Environment variable `NAVAL_GALLERY_IMAGE_DIR` overrides auto-detection

**Rationale**:
- Keeps git repository lightweight (~100KB vs hundreds of MB)
- Google Drive provides automatic cloud sync and backup
- Same manifests work on any machine with Google Drive mounted
- Separation of concerns: code in git, assets in cloud storage

**Consequence**: 
- Requires Google Drive mounted (or env var set) to run harvesters
- Images are not version-controlled (acceptable for large binary assets)
- Manifests ARE version-controlled as the source of truth for metadata

---

## Known Issues

1. **Duplicate IDs**: Some LOC images all named `loc_unknown.jpg`—need unique ID generation
2. **Noise in harvests**: Heuristics catch ~60-70% relevant images; rest is noise
3. **Missing metadata**: Many images lack ship name, era, navy—requires research
4. ~~**No staging workflow**~~: RESOLVED - Images now stored externally with Phase 1/2 classification

