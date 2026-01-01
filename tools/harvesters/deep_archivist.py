from internetarchive import search_items
import requests
import json
import os
import xml.etree.ElementTree as ET

# Deep Archivist
# Enhanced version of the pilot script

STAGING_DIR = "img/ia"
os.makedirs(STAGING_DIR, exist_ok=True)

def run():
    # Broader search
    query = 'subject:"naval architecture" AND mediatype:texts'
    print(f"[*] Deep Archivist searching: {query}")
    
    search = search_items(query)
    count = 0
    max_count = 5 # Process 5 volumes
    
    manifest = []
    headers = {'User-Agent': 'NavalPlateHarvester/1.0'}
    
    for result in search:
        if count >= max_count: break
        
        iid = result['identifier']
        print(f"[*] Analyzing {iid}...")
        
        # Scandata logic (same as pilot but optimized)
        url = f"https://archive.org/download/{iid}/{iid}_scandata.xml"
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200: continue
            
            root = ET.fromstring(r.content)
            
            volume_candidates = []
            for page in root.findall(".//page"):
                # Heuristic: Landscape only
                w = int(page.find("origWidth").text or 0)
                h = int(page.find("origHeight").text or 0)
                
                if w > h * 1.1:
                    leaf = page.get("leafNum")
                    volume_candidates.append({
                        "id": f"{iid}_{leaf}",
                        "url": f"https://archive.org/download/{iid}/page/n{leaf}.jpg",
                        "title": f"Plate from {iid}",
                        "source": iid,
                        "type": "lines", # Assumption for landscape
                        "navy": "Unknown"
                    })
            
            # Download top 3 from each valid volume
            for c in volume_candidates[:3]:
                path = os.path.join(STAGING_DIR, f"{c['id']}.jpg")
                if not os.path.exists(path):
                    print(f"    [+] Downloading {c['id']}")
                    img_r = requests.get(c['url'], timeout=15)
                    with open(path, 'wb') as f:
                        f.write(img_r.content)
                c['local_path'] = f"img/ia/{c['id']}.jpg"
                manifest.append(c)
                
            count += 1
            
        except Exception as e:
            print(f"    [!] Error: {e}")
            
    with open("data/ia_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

if __name__ == "__main__":
    run()
