import requests
import json
import os

# Official Channels
# Library of Congress API

STAGING_DIR = "img/loc"
os.makedirs(STAGING_DIR, exist_ok=True)

def run():
    print("[*] Contacting Library of Congress...")
    
    # LoC search for "monitor drawings" or similar to get old ships
    base_url = "https://www.loc.gov/photos/"
    params = {
        "q": "ship engineering drawing",
        "fo": "json",
        "fa": "online-format:image" 
    }
    
    try:
        r = requests.get(base_url, params=params, timeout=15)
        data = r.json()
        
        results = data.get('results', [])
        print(f"[*] Found {len(results)} items in LoC results")
        
        manifest = []
        
        for item in results[:10]:
            try:
                title = item.get('title', 'Unknown')
                # Image URLs are in 'image_url' list, often ending in .jpg
                img_urls = item.get('image_url', [])
                if not img_urls: continue
                
                # Pick the largest one usually last or specifically named
                best_url = img_urls[-1] 
                
                # Clean ID
                pk = item.get('pk', 'unknown')
                filename = f"loc_{pk}.jpg"
                path = os.path.join(STAGING_DIR, filename)
                
                if not os.path.exists(path):
                    print(f"    [+] Downloading {title[:30]}...")
                    ir = requests.get(best_url, timeout=15)
                    with open(path, 'wb') as f:
                        f.write(ir.content)
                        
                manifest.append({
                    "id": f"loc_{pk}",
                    "title": title,
                    "url": best_url,
                    "local_path": f"img/loc/{filename}",
                    "source": "Library of Congress",
                    "type": "profile"
                })
            except Exception as e:
                print(f"    [!] Item error: {e}")
                
        with open("data/loc_manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)
            
    except Exception as e:
        print(f"[!] LoC API Error: {e}")

if __name__ == "__main__":
    run()
