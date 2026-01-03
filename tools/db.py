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
        
        -- Classification results (Phase 1)
        ship_type TEXT,
        view_type TEXT,
        navy TEXT,
        era TEXT,
        
        -- Rich extraction (Phase 2)
        ship_name TEXT,
        ship_class TEXT,
        hull_number TEXT,
        shipyard TEXT,
        displacement TEXT,
        armament TEXT,
        dimensions TEXT,
        
        -- Enhanced fields (New)
        propulsion TEXT,
        armor TEXT,
        speed TEXT,
        complement TEXT,
        launch_date TEXT,
        commission_date TEXT,
        reasoning TEXT,
        
        confidence TEXT,
        raw_response TEXT,
        notes TEXT
    )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_analysis_status ON images(analysis_status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ship_type ON images(ship_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_navy ON images(navy)")
    
    conn.commit()
    conn.close()
    print(f"[*] Database initialized at {DB_PATH}")

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
        # Dynamic update based on provided results (to support Phase 2 enrichment without wiping Phase 1)
        update_fields = {
            'analysis_status': 'complete',
            'analyzed_at': now,
            'error_message': None
        }
        
        # Map of potentially available fields in results
        valid_columns = [
            'ship_type', 'view_type', 'navy', 'era',
            'ship_name', 'ship_class', 'hull_number', 'shipyard',
            'displacement', 'armament', 'dimensions',
            'propulsion', 'armor', 'speed', 'complement',
            'launch_date', 'commission_date', 'reasoning',
            'confidence', 'notes'
        ]
        
        for col in valid_columns:
            if col in results and results[col] is not None:
                update_fields[col] = results[col]
                
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
    
    # Clean up raw_response for JSON export
    for entry in data:
        if entry.get('raw_response'):
            try:
                entry['raw_response'] = json.loads(entry['raw_response'])
            except:
                pass

    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"[*] Manifest exported to {output_path}")

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

if __name__ == "__main__":
    init_db()
    import_manifest(DATA_DIR / "master_manifest.json")
