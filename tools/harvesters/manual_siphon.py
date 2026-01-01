import os
import json
import requests
import xml.etree.ElementTree as ET

# ONI Manual Siphon
# Targets known WWII ONI Recognition Manuals on Internet Archive

STAGING_DIR = "img/oni"
os.makedirs(STAGING_DIR, exist_ok=True)
DATA_DIR = "data"

# Known IDs for ONI manuals or similar recognition books
ONI_IDS = [
    "oni-222-r-naval-vessels-of-russia",
    "oni-200-naval-vessels-of-the-united-states",
    # Falling back to generic if these specific IDs fail in testing, 
    # but these are typical identifiers.
]

def get_scandata_and_find_plates(item_id):
    # Similar to smart_harvester but more aggressive for ONI manuals
    # In recognition manuals, almost EVERY page is a "plate".
    url = f"https://archive.org/download/{item_id}/{item_id}_scandata.xml"
    print(f"[*] Scanning ONI Manual: {item_id}")
    
    headers = {'User-Agent': 'NavalPlateHarvester/1.0'}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200: return []
        
        root = ET.fromstring(r.content)
        candidates = []
        
        for page in root.findall(".//page"):
            leaf = page.get("leafNum")
            # In ONI manuals, we just want good regular pages, 
            # maybe skip the first 10 (front matter).
            if int(leaf) < 10: continue
            
            # Simple heuristic: Just grab every 5th page to sample the book
            # Real implementation would OCR for "Profile" but we want speed.
            if int(leaf) % 5 == 0:
                candidates.append({
                    "id": f"{item_id}_{leaf}",
                    "item_id": item_id,
                    "leaf": leaf,
                    "url": f"https://archive.org/download/{item_id}/page/n{leaf}.jpg",
                    "title": f"ONI Plate (Leaf {leaf})",
                    "source": item_id,
                    "navy": "Unknown",
                    "type": "profile" 
                })
                
        return candidates
    except Exception as e:
        print(f"[!] Error: {e}")
        return []

def download(item):
    path = os.path.join(STAGING_DIR, f"{item['id']}.jpg")
    if os.path.exists(path):
        item['local_path'] = f"img/oni/{item['id']}.jpg"
        return item
        
    try:
        r = requests.get(item['url'], timeout=15)
        with open(path, 'wb') as f:
            f.write(r.content)
        item['local_path'] = f"img/oni/{item['id']}.jpg"
        return item
    except:
        return None

def run():
    all_manifest = []
    
    # If the specific ONI IDs don't exist, search for them first
    # For this script we'll search for "ONI recognition manual" to be safe
    from internetarchive import search_items
    search = search_items('title:"recognition manual" AND mediatype:texts')
    
    ids = []
    for item in search:
        ids.append(item['identifier'])
        if len(ids) >= 3: break
        
    for i in ids:
        candidates = get_scandata_and_find_plates(i)
        # Take top 5 from each
        for c in candidates[:5]:
            res = download(c)
            if res: all_manifest.append(res)
            
    with open("data/oni_manifest.json", "w") as f:
        json.dump(all_manifest, f, indent=2)

if __name__ == "__main__":
    run()
