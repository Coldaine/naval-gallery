import requests
import os
import sys
import json
import re

# Add parent to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_staging_dir, get_relative_path, validate_config, DATA_DIR

# Wikimedia Commons Harvester
# Targets "Ship_plans" categories

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def search_category(category, depth=0, max_depth=1):
    print(f"[*] Scanning Category: {category} (Depth: {depth})")
    url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": category,
        "cmtype": "file|subcat",
        "cmlimit": 500,
        "format": "json"
    }
    headers = {"User-Agent": USER_AGENT}
    
    try:
        r = requests.get(url, params=params, headers=headers)
        data = r.json()
        
        results = []
        subcats = []
        
        for member in data.get('query', {}).get('categorymembers', []):
            title = member['title']
            if member['ns'] == 6: # File
                # Filter for "Plan", "Profile", "Lines" in title
                lower_title = title.lower()
                if any(x in lower_title for x in ['plan', 'profile', 'lines', 'diagram', 'layout', 'drawing']):
                    results.append(title)
            elif member['ns'] == 14 and depth < max_depth: # Category
                subcats.append(title)
                
        # Recurse
        for sub in subcats:
            results.extend(search_category(sub, depth+1, max_depth))
            
        return results
    except Exception as e:
        print(f"[!] Error processing {category}: {e}")
        return []

def get_file_info(titles):
    if not titles: return []
    
    # Batch requests (max 50)
    chunked = [titles[i:i + 50] for i in range(0, len(titles), 50)]
    file_data = []
    
    url = "https://commons.wikimedia.org/w/api.php"
    
    for chunk in chunked:
        params = {
            "action": "query",
            "titles": "|".join(chunk),
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "format": "json"
        }
        headers = {"User-Agent": USER_AGENT}
        try:
            r = requests.get(url, params=params, headers=headers)
            pages = r.json().get('query', {}).get('pages', {})
            
            for pid, page in pages.items():
                if 'imageinfo' in page:
                    info = page['imageinfo'][0]
                    meta = info.get('extmetadata', {})
                    
                    desc = meta.get('ImageDescription', {}).get('value', 'Unknown')
                    date = meta.get('DateTimeOriginal', {}).get('value', 'Unknown')
                    
                    # Strip HTML from date if present
                    if date and "<" in date:
                        date = re.sub(r'<[^>]*>', '', date).strip()
                    
                    output = {
                        "id": f"wiki_{page['pageid']}",
                        "title": page['title'].replace("File:", ""),
                        "url": info['url'],
                        "desc": desc,
                        "date": date,
                        "source": "Wikimedia Commons"
                    }
                    file_data.append(output)
        except Exception as e:
            print(f"[!] Info fetch error: {e}")
            
    return file_data

def download_file(item, staging_dir):
    ext = item['url'].split('.')[-1]
    filename = f"{item['id']}.{ext}"
    path = staging_dir / filename
    
    if path.exists():
        item['local_path'] = get_relative_path("wiki", filename)
        return item
        
    print(f"[+] Downloading: {item['title']} from {item['url']}")
    headers = {"User-Agent": USER_AGENT}
    try:
        r = requests.get(item['url'], headers=headers, timeout=20)
        if r.status_code == 200:
            with open(path, 'wb') as f:
                f.write(r.content)
            item['local_path'] = get_relative_path("wiki", filename)
            return item
        else:
            print(f"[!] Download failed for {item['id']}: Status {r.status_code}")
            return None
    except Exception as e:
        print(f"[!] Download exception for {item['id']}: {e}")
        return None

def run():
    # Validate config before doing anything
    validate_config()
    
    STAGING_DIR = get_staging_dir("wiki")
    
    # Seed categories
    seeds = [
        "Category:Ship_plans",
        "Category:Naval_line_drawings",
        "Category:Diagrams_of_ships_from_Brassey's_Naval_Annual",
        "Category:Diagrams_of_ships_from_Jane's_Fighting_Ships"
    ]
    
    all_titles = []
    for seed in seeds:
        all_titles.extend(search_category(seed, max_depth=2))
        
    print(f"[*] Found {len(all_titles)} candidate files.")
    
    # Get metadata
    items = get_file_info(all_titles[:500]) # Increased limit
    
    # Download
    manifest = []
    for item in items:
        res = download_file(item, STAGING_DIR)
        if res: manifest.append(res)
        
    with open(DATA_DIR / "wiki_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

if __name__ == "__main__":
    run()
