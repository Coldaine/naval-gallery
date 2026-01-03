import requests
import os
import sys
import json
import re

# Add parent to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_staging_dir, get_relative_path, validate_config, DATA_DIR

# Blueprints Crawler
# Targets NavSource (respectfully) for specific class pages

USER_AGENT = "NavalPlateHarvester/1.0"

def run():
    # Validate config before doing anything
    validate_config()
    
    STAGING_DIR = get_staging_dir("blueprints")
    
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
                path = STAGING_DIR / filename
                
                if not path.exists():
                    print(f"    [+] Found Plan: {filename}")
                    ir = requests.get(img_url, headers={'User-Agent': USER_AGENT})
                    with open(path, 'wb') as f:
                        f.write(ir.content)
                        
                manifest.append({
                    "id": filename.split(".")[0],
                    "title": f"NavSource Plan {filename}",
                    "url": img_url,
                    "local_path": get_relative_path("blueprints", filename),
                    "source": "NavSource",
                    "type": "deck" # Guess
                })
                
    except Exception as e:
        print(f"[!] Error: {e}")
        
    with open(DATA_DIR / "blueprints_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

if __name__ == "__main__":
    run()
