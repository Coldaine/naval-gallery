import requests
import os
import json
import re

# Blueprints Crawler
# Targets NavSource (respectfully) for specific class pages

STAGING_DIR = "img/blueprints"
os.makedirs(STAGING_DIR, exist_ok=True)
USER_AGENT = "NavalPlateHarvester/1.0"

def run():
    print("[*] Crawling NavSource for Plan Views...")
    
    # Target a specific portal page that lists classes
    # NavSource battleship index
    target_url = "http://www.navsource.org/archives/01/01idx.htm" 
    
    manifest = []
    
    try:
        # 1. Fetch Index
        r = requests.get(target_url, headers={'User-Agent': USER_AGENT})
        # Simple regex to find links to ship pages "01/01XX.htm"
        links = set(re.findall(r'href="(\.\.\/01\/\d+\.htm)"', r.text))
        
        # We need to construct full URLs
        # base is http://www.navsource.org/archives/01/
        
        print(f"[*] Found {len(links)} potential ship pages.")
        
        # Visit top 5
        for link in list(links)[:5]:
            # Correct relative path
            # link is like "../01/57.htm" -> remove ".."
            clean_link = link.replace("..", "")
            page_url = f"http://www.navsource.org/archives{clean_link}"
            
            print(f"    Visiting {page_url}")
            pr = requests.get(page_url, headers={'User-Agent': USER_AGENT})
            
            # 2. Look for "Plan" or "Line Drawing" images
            # NavSource often labels them or puts them in specific table rows
            # Heuristic: Look for images with 'drawing' or 'plan' in filename
            
            img_matches = re.findall(r'src="([^"]*(?:plan|draw|line)[^"]*\.jpg)"', pr.text, re.IGNORECASE)
            
            for img_rel in img_matches:
                # url join
                # page is archives/01/XX.htm, image is usually relative
                img_url = f"http://www.navsource.org/archives/01/{img_rel}"
                
                filename = img_rel.split("/")[-1]
                path = os.path.join(STAGING_DIR, filename)
                
                if not os.path.exists(path):
                    print(f"    [+] Found Plan: {filename}")
                    ir = requests.get(img_url, headers={'User-Agent': USER_AGENT})
                    with open(path, 'wb') as f:
                        f.write(ir.content)
                        
                manifest.append({
                    "id": filename.split(".")[0],
                    "title": f"NavSource Plan {filename}",
                    "url": img_url,
                    "local_path": f"img/blueprints/{filename}",
                    "source": "NavSource",
                    "type": "deck" # Guess
                })
                
    except Exception as e:
        print(f"[!] Error: {e}")
        
    with open("data/blueprints_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

if __name__ == "__main__":
    run()
