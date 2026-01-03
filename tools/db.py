import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "gallery.db"

def init_db():
    "Initialize SQLite database and image table."
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS images (
        id TEXT PRIMARY KEY,
        local_path TEXT NOT NULL,
        url TEXT,
        source TEXT,
        title TEXT,
        desc TEXT,
        date TEXT,
        
        -- Analysis state
        analysis_status TEXT DEFAULT 'pending',
        analyzed_at TIMESTAMP,
        error_message TEXT,
        
        -- Organization state
        organization_status TEXT DEFAULT 'pending', -- pending | organized | error
        
        -- Image structure (BroadsideStudio alignment)
        image_type TEXT,                -- single_view, multi_view_stacked, multi_view_grid, etc.
        
        -- View metadata (structural columns - first class properties)
        view_type TEXT,                 -- side_profile, plan_view, bow_view, stern_view, cross_section, detail
        view_style TEXT,                -- line_drawing_bw, line_drawing_color, filled_color, shaded, photograph, painting
        orientation TEXT,               -- bow_left, bow_right, bow_up, bow_down
        bounds JSON,                    -- { x, y, width, height } if cropped
        
        -- Ship identification
        ship_type TEXT,                 -- battleship, cruiser, destroyer, submarine, carrier, auxiliary
        ship_name TEXT,
        ship_class TEXT,
        hull_number TEXT,
        navy TEXT,
        era TEXT,                       -- pre_dreadnought, dreadnought, interwar, wwii, post_war
        is_historical BOOLEAN,          -- false if hypothetical/fictional
        designer TEXT,                  -- Artist/designer attribution
        
        -- Quality assessment (BroadsideStudio alignment)
        silhouette_clarity TEXT,        -- clean, moderate, noisy
        annotation_density TEXT,        -- none, light, heavy  
        resolution_quality TEXT,        -- high, medium, low
        extraction_tier INTEGER,        -- 1-5 per DATA-003 (1=digital best, 5=unsuitable)
        suitable_for_extraction BOOLEAN,
        quality_issues JSON,            -- ["watermark", "low contrast", etc.]
        
        -- Text extraction
        text_content JSON,              -- [{ text, location: {x,y}, textType, confidence }]
        
        -- Technical specs (Phase 2 enrichment)
        shipyard TEXT,
        displacement TEXT,
        armament TEXT,
        dimensions TEXT,
        propulsion TEXT,
        armor TEXT,
        speed TEXT,
        complement TEXT,
        launch_date TEXT,
        commission_date TEXT,
        
        -- Analysis metadata
        reasoning TEXT,
        confidence REAL,                -- 0.0 - 1.0 (numeric, not text)
        raw_response TEXT,
        notes TEXT
    )
    """)
    
    # Basic indexes (columns guaranteed to exist)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_analysis_status ON images(analysis_status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ship_type ON images(ship_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_navy ON images(navy)")
    
    conn.commit()
    conn.close()
    print(f"[*] Database initialized at {DB_PATH}")
    
    # Run migration to add new columns to existing tables
    migrate_db()



def migrate_db():
    """Add new columns if they don't exist (for existing databases)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get existing columns
    cursor.execute("PRAGMA table_info(images)")
    existing_cols = {row[1] for row in cursor.fetchall()}
    
    # New columns to add
    new_columns = [
        ("image_type", "TEXT"),
        ("view_style", "TEXT"),
        ("orientation", "TEXT"),
        ("bounds", "JSON"),
        ("is_historical", "BOOLEAN"),
        ("designer", "TEXT"),
        ("silhouette_clarity", "TEXT"),
        ("annotation_density", "TEXT"),
        ("resolution_quality", "TEXT"),
        ("extraction_tier", "INTEGER"),
        ("suitable_for_extraction", "BOOLEAN"),
        ("quality_issues", "JSON"),
        ("text_content", "JSON"),
    ]
    
    added = 0
    for col_name, col_type in new_columns:
        if col_name not in existing_cols:
            cursor.execute(f"ALTER TABLE images ADD COLUMN {col_name} {col_type}")
            added += 1
    
    if added > 0:
        # Create new indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_view_type ON images(view_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_extraction_tier ON images(extraction_tier)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_suitable ON images(suitable_for_extraction)")
        
        conn.commit()
        print(f"[*] Migration complete. Added {added} new columns.")
    else:
        print("[*] Database schema already up to date.")
    
    conn.close()


def import_manifest(manifest_path):
    "Import entries from JSON manifest into database."
    if not os.path.exists(manifest_path):
        print(f"[!] Manifest not found: {manifest_path}")
        return

    with open(manifest_path, 'r') as f:
        data = json.load(f)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    new_count = 0
    update_count = 0
    
    for entry in data:
        img_id = entry.get('id')
        if not img_id:
            continue
            
        local_path = entry.get('local_path', '')
        url = entry.get('url', '')
        source = entry.get('source', '')
        title = entry.get('title', '')
        desc = entry.get('desc', '')
        date = entry.get('date', '')
        
        # Check if exists
        cursor.execute("SELECT id FROM images WHERE id = ?", (img_id,))
        if cursor.fetchone():
            # Update existing
            cursor.execute("""
                UPDATE images SET 
                    local_path = ?, url = ?, source = ?, title = ?, desc = ?, date = ?
                WHERE id = ?
            """, (local_path, url, source, title, desc, date, img_id))
            update_count += 1
        else:
            # Insert new
            cursor.execute("""
                INSERT INTO images (id, local_path, url, source, title, desc, date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (img_id, local_path, url, source, title, desc, date))
            new_count += 1
            
    conn.commit()
    conn.close()
    print(f"[*] Manifest import complete. New: {new_count}, Updated: {update_count}")


def get_pending(limit=None):
    "Get images with 'pending' analysis status."
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = "SELECT * FROM images WHERE analysis_status = 'pending'"
    params = []
    if limit:
        query += " LIMIT ?"
        params.append(limit)
        
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def save_analysis(img_id, results, error=None):
    "Save analysis results or error."
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    now = datetime.now().isoformat()
    
    if error:
        cursor.execute("""
            UPDATE images SET 
                analysis_status = 'failed',
                analyzed_at = ?,
                error_message = ?
            WHERE id = ?
        """, (now, error, img_id))
    else:
        # Dynamic update based on provided results
        update_fields = {
            'analysis_status': 'complete',
            'analyzed_at': now,
            'error_message': None
        }
        
        # All valid columns (including new BroadsideStudio-aligned fields)
        valid_columns = [
            # Structure
            'image_type', 'view_type', 'view_style', 'orientation',
            # Identification
            'ship_type', 'ship_name', 'ship_class', 'hull_number', 
            'navy', 'era', 'is_historical', 'designer',
            # Quality
            'silhouette_clarity', 'annotation_density', 'resolution_quality',
            'extraction_tier', 'suitable_for_extraction',
            # Technical specs
            'shipyard', 'displacement', 'armament', 'dimensions',
            'propulsion', 'armor', 'speed', 'complement',
            'launch_date', 'commission_date',
            # Metadata
            'reasoning', 'confidence', 'notes'
        ]
        
        for col in valid_columns:
            if col in results and results[col] is not None:
                update_fields[col] = results[col]
        
        # Handle JSON fields
        json_fields = ['bounds', 'quality_issues', 'text_content']
        for col in json_fields:
            if col in results and results[col] is not None:
                update_fields[col] = json.dumps(results[col])
                
        if 'raw_response' in results:
            update_fields['raw_response'] = json.dumps(results['raw_response'])

        # Construct SQL
        set_clause = ", ".join([f"{k} = ?" for k in update_fields.keys()])
        values = list(update_fields.values())
        values.append(img_id)
        
        query = f"UPDATE images SET {set_clause} WHERE id = ?"
        cursor.execute(query, values)
        
    conn.commit()
    conn.close()


def get_ready_to_organize(limit=None):
    "Get images that are complete but not yet organized."
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = "SELECT * FROM images WHERE analysis_status = 'complete' AND organization_status = 'pending'"
    params = []
    if limit:
        query += " LIMIT ?"
        params.append(limit)
        
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_organization(img_id, new_path, status='organized'):
    "Update organization status and physical path."
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE images SET 
            organization_status = ?,
            local_path = ?
        WHERE id = ?
    """, (status, new_path, img_id))
    conn.commit()
    conn.close()


def export_manifest(output_path):
    "Export all images to JSON manifest."
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM images")
    rows = cursor.fetchall()
    conn.close()
    
    data = [dict(row) for row in rows]
    
    # Parse JSON fields for export
    json_fields = ['raw_response', 'bounds', 'quality_issues', 'text_content']
    for entry in data:
        for field in json_fields:
            if entry.get(field):
                try:
                    entry[field] = json.loads(entry[field])
                except:
                    pass

    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"[*] Manifest exported to {output_path}")


def sync_frontend():
    "Export all analyzed images to images.js for the frontend."
    output_path = DATA_DIR / "images.js"
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM images")
    rows = cursor.fetchall()
    conn.close()
    
    data = [dict(row) for row in rows]
    
    # Parse JSON fields for frontend use
    json_fields = ['raw_response', 'bounds', 'quality_issues', 'text_content']
    for entry in data:
        for field in json_fields:
            if entry.get(field):
                try:
                    entry[field] = json.loads(entry[field])
                except:
                    pass

    with open(output_path, 'w') as f:
        f.write(f"const images = {json.dumps(data, indent=2)};")
    print(f"[*] Frontend synced to {output_path}")



def get_phase2_pending(limit=None):
    "Get images ready for Phase 2 enrichment (valid ships, Phase 1 complete)."
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Filter for completed items that are valid ships but missing Phase 2 data
    query = """
        SELECT * FROM images 
        WHERE analysis_status = 'complete' 
        AND (
            ship_type NOT LIKE 'N/A%'
            AND ship_type NOT LIKE 'Not %'
            AND ship_type != 'Unknown'
            AND ship_type NOT LIKE 'civil coding%'
            AND ship_type NOT LIKE 'Indeterminate%'
        )
        AND ship_class IS NULL -- Phase 2 field
    """
    params = []
    if limit:
        query += " LIMIT ?"
        params.append(limit)
        
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_extraction_candidates(tier_max=3, limit=None):
    """Get images suitable for extraction (Tier 1-3 by default)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = """
        SELECT * FROM images 
        WHERE suitable_for_extraction = 1
        AND extraction_tier <= ?
        ORDER BY extraction_tier ASC
    """
    params = [tier_max]
    if limit:
        query += " LIMIT ?"
        params.append(limit)
        
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


if __name__ == "__main__":
    init_db()
    migrate_db()  # Add new columns to existing DB
    import_manifest(DATA_DIR / "master_manifest.json")
