import requests
import os
import sys
import json
import re
import time
from urllib.parse import urljoin

# Add parent to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_staging_dir, get_relative_path, validate_config, DATA_DIR

# Dreadnought Project Scraper
# Targets http://www.dreadnoughtproject.org for high-quality WWI ship plans

USER_AGENT = "NavalPlateHarvester/1.0"

def run():
    # Validate config before doing anything
    validate_config()
    
    STAGING_DIR = get_staging_dir("dreadnought")
    
    print("[*] Exhaustive Dreadnought Project Scrape...")
    
    # Target the plans directory
    base_url = "http://www.dreadnoughtproject.org/plans/"
    
    manifest = []
    found_images = []
    
    try:
        print(f"[*] Checking index: {base_url}")
        r = requests.get(base_url, headers={'User-Agent': USER_AGENT}, timeout=10)
        if r.status_code != 200: 
            print(f"[!] Failed to reach {base_url}")
            return
        
        # Find all subdirectories (ship folders)
        subdirs = re.findall(r'href="([^"/]+?/)"', r.text)
        print(f"[*] Found {len(subdirs)} ship directories. Scanning ALL...")
        
        for subdir in subdirs:
            ship_url = urljoin(base_url, subdir)
            print(f"    Scanning {subdir}")
            
            try:
                rs = requests.get(ship_url, headers={'User-Agent': USER_AGENT}, timeout=10)
                if rs.status_code != 200: 
                    continue
                
                # Find all JPGs in this ship's directory
                imgs = re.findall(r'href="([^"]*?\.jpg)"', rs.text, re.IGNORECASE)
                for img in imgs:
                    full_img_url = urljoin(ship_url, img)
                    if full_img_url not in found_images:
                        found_images.append(full_img_url)
            except Exception as e:
                print(f"    [!] Error scanning {subdir}: {e}")
        
        print(f"[*] Found {len(found_images)} total images. Downloading ALL (no limit)...")
        
        # Download all images - NO LIMIT
        for idx, img_url in enumerate(found_images):
            filename = img_url.split("/")[-1]
            safe_id = re.sub(r'[^\w\-]', '_', filename.split(".")[0])
            path = STAGING_DIR / filename
            
            if path.exists() and path.stat().st_size > 1000:
                # Already downloaded
                manifest.append({
                    "id": f"tdp_{safe_id}",
                    "title": f"Dreadnought Project: {filename}",
                    "url": img_url,
                    "local_path": get_relative_path("dreadnought", filename),
                    "source": "Dreadnought Project",
                    "type": "deck"
                })
                continue
            
            print(f"    [{idx+1}/{len(found_images)}] Downloading {filename}...")
            try:
                time.sleep(1.5)  # Polite delay
                ir = requests.get(img_url, headers={'User-Agent': USER_AGENT}, timeout=20)
                if ir.status_code == 200:
                    with open(path, 'wb') as f:
                        f.write(ir.content)
                    
                    if path.stat().st_size > 1000:
                        manifest.append({
                            "id": f"tdp_{safe_id}",
                            "title": f"Dreadnought Project: {filename}",
                            "url": img_url,
                            "local_path": get_relative_path("dreadnought", filename),
                            "source": "Dreadnought Project",
                            "type": "deck"
                        })
                else:
                    print(f"    [!] HTTP {ir.status_code}: {img_url}")
            except Exception as e:
                print(f"    [!] Download error: {e}")
                
    except Exception as e:
        print(f"[!] Fatal error: {e}")
        
    print(f"[*] Scrape complete. {len(manifest)} images in manifest.")
    with open(DATA_DIR / "dreadnought_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

if __name__ == "__main__":
    run()
