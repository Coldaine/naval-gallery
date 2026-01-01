#!/usr/bin/env python3
import os
import json
import requests
import argparse
from internetarchive import search_items, get_item
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

# Constraints for "Naval Plates" based on calibration
# Hovgaard example: Standard 2912x4368, Foldout 4368x2912.
# Heuristic: Landscape orientation OR explicitly marked as Foldout/Plate.

STAGING_DIR = "../img/staging"
DATA_DIR = "../data"
os.makedirs(STAGING_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

def parse_scandata(item_id):
    """
    Fetches and parses scandata.xml for a given item.
    Returns a list of candidate pages (plates).
    """
    url = f"https://archive.org/download/{item_id}/{item_id}_scandata.xml"
    print(f"[DEBUG] Fetching: {url}")
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; NavalPlateHarvester/1.0; +http://example.com)'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"[DEBUG] Status Code: {response.status_code}")
        if response.status_code != 200:
            print(f"[-] No scandata found for {item_id}")
            return []
        
        root = ET.fromstring(response.content)
        ns = {'ns': 'http://archive.org/scandata'} # Namespaces can vary, usually none or simple
        
        candidates = []
        
        # Scandata structure is usually <book><pageData><page>...
        # We look for <page> elements
        
        for page in root.findall(".//page"):
            leaf_num = page.get("leafNum")
            
            # Extract metadata
            page_type = page.find("pageType")
            page_type = page_type.text if page_type is not None else ""
            
            orig_width = page.find("origWidth")
            orig_width = int(orig_width.text) if orig_width is not None else 0
            
            orig_height = page.find("origHeight")
            orig_height = int(orig_height.text) if orig_height is not None else 0
            
            add_to_access = page.find("addToAccessFormats")
            add_to_access = add_to_access.text if add_to_access is not None else "true"

            # Skip deleted/hidden pages
            if add_to_access == "false":
                continue

            # HEURISTICS
            is_foldout_type = page_type.lower() in ["foldout", "plate", "map", "chart"]
            is_landscape = orig_width > (orig_height * 1.1)  # 10% wider than tall
            is_super_wide = orig_width > 3500 # Absolute size check (Hovgaard plates are ~4000+)

            if is_foldout_type or is_landscape or is_super_wide:
                candidates.append({
                    "item_id": item_id,
                    "leafNum": leaf_num,
                    "pageType": page_type,
                    "width": orig_width,
                    "height": orig_height,
                    "img_url": f"https://archive.org/download/{item_id}/page/n{leaf_num}.jpg"
                })
                
        return candidates

    except Exception as e:
        print(f"[!] Error parsing scandata for {item_id}: {e}")
        return []

def download_image(candidate):
    """
    Downloads the high-res image for a candidate page.
    """
    filename = f"{candidate['item_id']}_{candidate['leafNum']}.jpg"
    filepath = os.path.join(STAGING_DIR, filename)
    
    if os.path.exists(filepath):
        print(f"[*] Skipping existing: {filename}")
        candidate['local_path'] = filepath
        return candidate

    print(f"[+] Downloading plate: {filename} ({candidate['pageType']} - {candidate['width']}x{candidate['height']})")
    try:
        r = requests.get(candidate['img_url'], stream=True, timeout=15)
        if r.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
            candidate['local_path'] = filepath
            return candidate
        else:
            print(f"[-] Failed to download {candidate['img_url']}")
            return None
    except Exception as e:
        print(f"[!] Error downloading {filename}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Naval Plate Harvester")
    parser.add_argument("--query", type=str, default="subject:\"naval architecture\" AND mediatype:texts", help="IA Search Query")
    parser.add_argument("--limit", type=int, default=3, help="Max volumes to scan")
    args = parser.parse_args()

    print(f"[*] Searching for: {args.query}")
    search = search_items(args.query)
    
    candidates = []
    processed_count = 0
    
    for result in search:
        if processed_count >= args.limit:
            break
            
        item_id = result['identifier']
        print(f"[*] Scanning volume: {item_id}")
        
        # Parse metadata
        plates = parse_scandata(item_id)
        if plates:
            print(f"    -> Found {len(plates)} candidate plates")
            candidates.extend(plates)
        else:
            print("    -> No plates found.")
            
        processed_count += 1

    print(f"[*] Total candidates found: {len(candidates)}")
    print("[*] Starting downloads...")

    downloaded_manifest = []
    
    # Download in parallel
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = executor.map(download_image, candidates)
        
        for res in results:
            if res:
                downloaded_manifest.append(res)

    # Save manifest
    manifest_path = os.path.join(DATA_DIR, "staging_manifest.json")
    with open(manifest_path, 'w') as f:
        json.dump(downloaded_manifest, f, indent=2)
        
    print(f"[*] Harvest complete. {len(downloaded_manifest)} images saved to {STAGING_DIR}")
    print(f"[*] Manifest saved to {manifest_path}")

if __name__ == "__main__":
    main()
