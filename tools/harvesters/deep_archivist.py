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
    # Broader search for technical drawings, excluding common low-yield DTIC reports
    query = '(subject:"naval architecture" OR subject:"ship plans" OR subject:"technical drawings") AND mediatype:texts AND NOT collection:dtic'
    print(f"[*] Deep Archivist searching: {query}")
    
    search = search_items(query)
    count = 0
    max_count = 10 
    
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
                width_node = page.find("origWidth")
                height_node = page.find("origHeight")
                
                if width_node is not None and height_node is not None:
                    w = int(width_node.text or 0)
                    h = int(height_node.text or 0)
                    
                    if w > h * 1.1 and w > 1000: # Ensure decent resolution
                        leaf = page.get("leafNum")
                        volume_candidates.append({
                            "id": f"{iid}_{leaf}",
                            "url": f"https://archive.org/download/{iid}/page/n{leaf}.jpg",
                            "title": f"Plate from {iid} (Leaf {leaf})",
                            "source": iid,
                            "type": "lines",
                            "navy": "Unknown"
                        })
            
            if not volume_candidates:
                print(f"    [-] No candidate plates found in {iid}")
                continue

            # Download top 5 from each valid volume
            for c in volume_candidates[:5]:
                path = os.path.join(STAGING_DIR, f"{c['id']}.jpg")
                if not os.path.exists(path):
                    print(f"    [+] Downloading {c['id']} ({c['url']})")
                    img_r = requests.get(c['url'], timeout=15)
                    if img_r.status_code == 200:
                        with open(path, 'wb') as f:
                            f.write(img_r.content)
                    else:
                        print(f"    [!] Download failed: {img_r.status_code}")
                        continue
                c['local_path'] = f"img/ia/{c['id']}.jpg"
                manifest.append(c)
                
            count += 1
            
        except Exception as e:
            print(f"    [!] Error processing {iid}: {e}")
            
    with open("data/ia_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

if __name__ == "__main__":
    run()
