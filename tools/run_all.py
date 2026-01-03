import os
import sys
import subprocess
import json
import glob
from pathlib import Path

# Add to path for config import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import validate_config, DATA_DIR

def run():
    # Validate config BEFORE running any harvesters
    validate_config()
    
    scripts = [
        "tools/harvesters/wiki_walker.py",
        "tools/harvesters/manual_siphon.py",
        "tools/harvesters/deep_archivist.py",
        "tools/harvesters/official_channels.py",
        "tools/harvesters/blueprints_crawler.py",
        "tools/harvesters/dreadnought_scraper.py",
        # Pinterest is optional - requires separate credentials
        # "tools/harvesters/pinterest_scraper.py"
    ]
    
    print("=== STARTING NAVAL HARVEST ===")
    
    for script in scripts:
        print(f"\n>>> Running {script}...")
        try:
            subprocess.run([sys.executable, script], check=False)
        except Exception as e:
            print(f"Failed to run {script}: {e}")
            
    print("\n=== HARVEST COMPLETE ===")
    print("Aggregating manifest...")
    
    all_images_map = {}
    source_counts = {}
    
    # Load all produced JSONs
    files = glob.glob(str(DATA_DIR / "*_manifest.json"))
    for fpath in files:
        if "master_manifest.json" in fpath: continue  # Don't include the master in itself
        source_name = os.path.basename(fpath).replace("_manifest.json", "")
        try:
            with open(fpath, "r") as f:
                data = json.load(f)
                count = 0
                for item in data:
                    if item['id'] not in all_images_map:
                        all_images_map[item['id']] = item
                        count += 1
                source_counts[source_name] = count
        except Exception as e:
            print(f"Error reading {fpath}: {e}")
            
    all_images = list(all_images_map.values())
    
    # Save master manifest
    with open(DATA_DIR / "master_manifest.json", "w") as f:
        json.dump(all_images, f, indent=2)

    # Prepare for frontend: Ensure local_path has 'img/' prefix if not already present
    frontend_images = []
    for img in all_images:
        img_copy = img.copy()
        if 'local_path' in img_copy and not img_copy['local_path'].startswith('img/'):
            img_copy['local_path'] = f"img/{img_copy['local_path']}"
        frontend_images.append(img_copy)
        
    print("\nSUMMARY:")
    print("-" * 30)
    for source, count in source_counts.items():
        print(f"{source:<15}: {count} images")
    print("-" * 30)
    print(f"Total Unique Images (Deduplicated): {len(all_images)}")
    print("-" * 30)
    
    # Update images.js for frontend
    with open(DATA_DIR / "images.js", "w") as f:
        f.write(f"const images = {json.dumps(frontend_images, indent=2)};")

if __name__ == "__main__":
    run()
