import requests
import os
import json
import re
from urllib.parse import urljoin

# Dreadnought Project Scraper
# Targets http://www.dreadnoughtproject.org for high-quality WWI ship plans

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../../"))
STAGING_DIR = os.path.join(PROJECT_ROOT, "img/dreadnought")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

os.makedirs(STAGING_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
USER_AGENT = "NavalPlateHarvester/1.0"

def run():
    print("[*] Scraping Dreadnought Project...")
    
    # Target specific open directory structure for plans
    # Based on verification, the site exists. We try the known /plans directory.
    target_urls = [
        "http://www.dreadnoughtproject.org/plans/"
    ]
    
    manifest = []
    
    try:
        found_images = []
        
        for url in target_urls:
            print(f"[*] Checking index: {url}")
            try:
                r = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=10)
                if r.status_code != 200: 
                    print(f"    [!] Failed to reach {url}")
                    continue
                
                # First, find subdirectories (they end in /)
                # Apache listings: <a href="SM_Kaiser_1912/">
                subdirs = re.findall(r'href="([^"/]+?/)"', r.text)
                
                print(f"[*] Found {len(subdirs)} ship directories. Scanning all...")
                
                for subdir in subdirs:
                    ship_url = urljoin(url, subdir)
                    print(f"    Scanning {ship_url}")
                    
                    rs = requests.get(ship_url, headers={'User-Agent': USER_AGENT}, timeout=10)
                    if rs.status_code != 200: continue
                    
                    # Find JPGs in subdirectory
                    imgs = re.findall(r'href="([^"]*?\.jpg)"', rs.text, re.IGNORECASE)
                    for img in imgs:
                        full_img_url = urljoin(ship_url, img)
                        if full_img_url not in found_images:
                            found_images.append(full_img_url)

            except Exception as e:
                print(f"    [!] Error checking {url}: {e}")
        
        print(f"[*] Found {len(found_images)} potential plan images.")
        
        max_downloads = 100
        count = 0
        
        for img_url in found_images:
            if count >= max_downloads: break
            
            filename = img_url.split("/")[-1]
            # Basic cleanup of filename for id
            safe_id = re.sub(r'[^\w\-]', '_', filename.split(".")[0])
            
            print(f"    [+] Downloading {filename}...")
            try:
                path = os.path.join(STAGING_DIR, filename)
                if not os.path.exists(path):
                    print(f"    [+] Downloading {filename}...")
                    import time
                    time.sleep(2) # Avoid 429
                    ir = requests.get(img_url, headers={'User-Agent': USER_AGENT}, timeout=15)
                    if ir.status_code == 200:
                        with open(path, 'wb') as f:
                            f.write(ir.content)
                    else:
                        print(f"    [!] Failed to download {img_url}: {ir.status_code}")
                        continue
                
                # Verify size to avoid 404/error pages
                if os.path.exists(path) and os.path.getsize(path) > 1000:
                    count += 1
                    manifest.append({
                        "id": safe_id,
                        "title": f"Dreadnought Project: {filename}",
                        "url": img_url,
                        "local_path": f"img/dreadnought/{filename}",
                        "source": "Dreadnought Project",
                        "type": "deck"
                    })
            except Exception as e:
                print(f"    [!] Download error: {e}")

    except Exception as e:
        print(f"[!] Error: {e}")
        
    with open(os.path.join(DATA_DIR, "dreadnought_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

if __name__ == "__main__":
    run()
