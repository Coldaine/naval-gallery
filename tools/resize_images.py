#!/usr/bin/env python3
"""
Resize images that are too large for the vision model.
Finds images that failed with 'too large' errors and resizes them.
"""

import os
import sys
import sqlite3
from pathlib import Path
from PIL import Image

# Add to path for config import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_image_dir, validate_config, DATA_DIR

DB_PATH = DATA_DIR / "gallery.db"

def get_oversized_failures():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, local_path FROM images 
        WHERE analysis_status = 'failed' 
        AND error_message LIKE '%too large%'
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def resize_image(relative_path, target_size_mb=4.5):
    """Resize image to be under target_size_mb."""
    # Images are stored relative to the image directory
    img_dir = get_image_dir()
    img_path = img_dir / relative_path
        
    if not img_path.exists():
        print(f"[-] File not found: {img_path}")
        return False
        
    start_size = img_path.stat().st_size / (1024 * 1024)
    if start_size < target_size_mb:
        print(f"[*] {img_path.name} is already {start_size:.2f}MB (under limit).")
        return True
        
    print(f"[*] Resizing {img_path.name} ({start_size:.2f}MB)...")
    
    try:
        with Image.open(img_path) as img:
            # Convert to RGB if needed (e.g. RGBA to JPG)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
                
            # Initial quality reduction
            quality = 95
            scale = 0.9
            
            # Iteratively reduce
            while True:
                # Save to temp
                temp_path = img_path.with_suffix('.tmp.jpg')
                img.save(temp_path, "JPEG", quality=quality)
                
                new_size = temp_path.stat().st_size / (1024 * 1024)
                
                if new_size < target_size_mb:
                    print(f"    -> Success: {new_size:.2f}MB (Quality: {quality})")
                    temp_path.replace(img_path)
                    return True
                
                # Reduce more
                quality -= 10
                if quality < 30:
                    # Resize dimensions if quality too low
                    width, height = img.size
                    new_dims = (int(width * scale), int(height * scale))
                    print(f"    -> Resizing dimensions to {new_dims}...")
                    img = img.resize(new_dims, Image.Resampling.LANCZOS)
                    quality = 85 # Reset quality for new dimensions
                    
    except Exception as e:
        print(f"[!] Error resizing {img_path}: {e}")
        return False

def reset_status(img_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE images SET 
            analysis_status = 'pending',
            error_message = NULL
        WHERE id = ?
    """, (img_id,))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    # Validate config first
    validate_config()
    
    failures = get_oversized_failures()
    if not failures:
        print("[*] No oversized failures found.")
        sys.exit(0)
        
    print(f"[*] Found {len(failures)} oversized images.")
    
    for item in failures:
        if resize_image(item['local_path']):
            reset_status(item['id'])
            print(f"[+] Reset status for {item['id']}")
