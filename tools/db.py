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
        
        -- Classification results (Phase 1)
        ship_type TEXT,
        view_type TEXT,
        navy TEXT,
        era TEXT,
        
        -- Rich extraction (Phase 2)
        ship_name TEXT,
        ship_class TEXT,
        displacement TEXT,
        armament TEXT,
        dimensions TEXT,
        
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
    if limit:
        query += f" LIMIT {limit}"
        
    cursor.execute(query)
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
        cursor.execute("""
            UPDATE images SET 
                analysis_status = 'complete',
                analyzed_at = ?,
                ship_type = ?,
                view_type = ?,
                navy = ?,
                era = ?,
                ship_name = ?,
                ship_class = ?,
                displacement = ?,
                armament = ?,
                dimensions = ?,
                confidence = ?,
                raw_response = ?,
                notes = ?,
                error_message = NULL
            WHERE id = ?
        """, (
            now,
            results.get('ship_type'),
            results.get('view_type'),
            results.get('navy'),
            results.get('era'),
            results.get('ship_name'),
            results.get('ship_class'),
            results.get('displacement'),
            results.get('armament'),
            results.get('dimensions'),
            results.get('confidence'),
            json.dumps(results.get('raw_response')),
            results.get('notes'),
            img_id
        ))
        
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
    
    for entry in data:
        if entry.get('raw_response'):
            try:
                entry['raw_response'] = json.loads(entry['raw_response'])
            except:
                pass

    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"[*] Manifest exported to {output_path}")

if __name__ == "__main__":
    init_db()
    import_manifest(DATA_DIR / "master_manifest.json")
