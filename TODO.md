# Naval Gallery Integration TODO

Last updated: 2026-01-13

## Current State

### What's Done (Schema Alignment)

The database schema has been aligned with ProjectBroadsideStudio Stage 1:

| naval-gallery Column | Studio Equivalent | Status |
|---------------------|-------------------|--------|
| `view_type` | `VisionAnalysisResult.views[].view_type` | Aligned |
| `view_style` | `VisionAnalysisResult.views[].style` | Aligned |
| `extraction_tier` | Quality tier (1-5) | Aligned |
| `suitable_for_extraction` | Boolean flag | Aligned |
| `silhouette_clarity` | `none/light/heavy` | Aligned |
| `ship_type`, `navy`, `era` | Taxonomy terms | Aligned |

The `get_extraction_candidates(tier_max=3)` function is ready to filter images suitable for Studio ingestion.

### What's NOT Done (Actual Integration)

| Gap | Description |
|-----|-------------|
| **Different databases** | Gallery uses local SQLite; Studio uses PostgreSQL on Zo |
| **Different storage** | Gallery images in Google Drive; Studio expects artifact store |
| **No sync mechanism** | No automated way to push images/metadata to Studio |
| **No path translation** | Google Drive paths don't map to Studio's storage |

**Bottom line**: Schema is aligned but there's no actual data flow between the systems.

---

## Integration Tasks

### Phase 1: Export Layer

Create an export mechanism that Studio can consume.

- [ ] **Export to Studio-compatible JSON**
  - New command: `uv run python tools/export_for_studio.py`
  - Output: `data/studio_export.json` with paths and metadata
  - Filter: Only `extraction_tier <= 3` and `suitable_for_extraction = True`

- [ ] **Define path translation strategy**
  - Option A: Copy images to Studio's artifact store
  - Option B: Studio reads from Google Drive directly (requires mount on Zo)
  - Option C: Upload to shared S3/cloud storage

### Phase 2: Database Sync

Push metadata directly to Studio's PostgreSQL.

- [ ] **Create sync script**
  - Connect to Studio's PostgreSQL on Zo
  - Upsert records with matching schema
  - Track sync state (last_synced_at)

- [ ] **Handle artifact references**
  - Store image URLs or paths that Studio can resolve
  - May require running harvesters on Zo directly

### Phase 3: Pipeline Integration

Make naval-gallery a true upstream pipeline.

- [ ] **MCP tool for Studio**
  - `get_candidates(tier_max, limit)` - returns images ready for ingestion
  - `mark_ingested(ids)` - updates sync state

- [ ] **Automated trigger**
  - On new harvest → notify Studio
  - Studio pulls candidates on demand

---

## Architecture Decision Needed

**Key insight:** Studio's artifact store is planned for `zo:~/navalforge/artifacts/`, NOT Google Drive.

### Option A: rsync to zo (Recommended)
```
naval-gallery (SQLite + Google Drive)
    │
    ▼ rsync approved images to zo
    │
zo:~/navalforge/inputs/naval-gallery/
    │
    ▼ Studio reads from zo
    │
PostgreSQL + artifacts on zo
```
- Pro: Single system of record (zo), no duplication once synced
- Con: Requires running rsync periodically

### Option B: Mount Google Drive on zo
```
naval-gallery (SQLite + Google Drive)
    │
    ├─────────────┐
    ▼             ▼
Google Drive ← rclone mount on zo
```
- Pro: No manual sync
- Con: Adds rclone dependency to zo, network latency

### Option C: Export manifests only
```
naval-gallery exports manifest.json with URLs
    │
    ▼
Studio downloads images on-demand from URLs
```
- Pro: No storage sync needed
- Con: Depends on external URLs staying valid

---

## Investigation Notes: ProjectBroadsideStudio Alignment

Before implementing integration, investigate these in Studio:

### Storage Status
- [ ] Is `zo:~/navalforge/` directory structure created?
- [ ] Is PostgreSQL on zo actually running and accessible?
- [ ] What's the current state of Tailscale connectivity to zo?
- [ ] Check `docs/infrastructure/artifact_storage.md` - much is marked "Not Implemented"

### Schema Compatibility
- [ ] Compare `naval-gallery/tools/db.py` columns with Studio's Stage 1 database schema
- [ ] Verify taxonomy enums match exactly (`view_type`, `ship_type`, `era` values)
- [ ] Check if Studio expects any fields naval-gallery doesn't have

### Open PRs to Review
Studio has 3 open PRs that may affect integration:
- [ ] **PR #11**: Hull Z-Level Extraction docs
- [ ] **PR #6**: Verifier-Corrector architecture (336 additions)
- [ ] **PR #5**: Verification stage analysis

### Key Files to Read in Studio
```
docs/infrastructure/artifact_storage.md    # Storage architecture (mostly planned)
docs/infrastructure/database_environments.md
src/navalforge/stage1/database/models.py   # Actual schema
docs/Stage1_Ingestion/                     # Stage 1 spec
```

### Questions to Answer
1. Does Studio have an "import from external source" flow, or does it expect to ingest raw images?
2. Should naval-gallery push to Studio, or should Studio pull from naval-gallery?
3. What's the minimum viable integration (manifest export? direct DB sync? MCP tool?)

---

## Quick Wins

Things that can be done without architectural decisions:

1. **Add `studio_ready` view to SQLite**
   ```sql
   CREATE VIEW studio_ready AS
   SELECT * FROM images
   WHERE suitable_for_extraction = 1
   AND extraction_tier <= 3;
   ```

2. **Export manifest with Studio-compatible paths**
   - Already have `export_manifest()` - just need path transformation

3. **Document the taxonomy mapping**
   - Ensure Gallery's terms exactly match Studio's enums

---

## Related Docs

- [ProjectBroadsideStudio Stage 1 Spec](../ProjectBroadsideStudio/docs/stages/stage1_ingestion/)
- [naval-gallery Architecture](docs/ARCHITECTURE.md)
- [Integration alignment commit](https://github.com/Coldaine/naval-gallery/commit/bd0a2ef)
