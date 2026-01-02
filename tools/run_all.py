import os
import subprocess
import json
import glob

def run():
    scripts = [
        "tools/harvesters/wiki_walker.py",
        "tools/harvesters/manual_siphon.py",
        "tools/harvesters/deep_archivist.py",
        "tools/harvesters/official_channels.py",
        "tools/harvesters/blueprints_crawler.py"
    ]
    
    print("=== STARTING NAVAL HARVEST ===")
    
    import sys
    for script in scripts:
        print(f"\n>>> Running {script}...")
        try:
            subprocess.run([sys.executable, script], check=False) # Use current interpreter
        except Exception as e:
            print(f"Failed to run {script}: {e}")
            
    print("\n=== HARVEST COMPLETE ===")
    print("Aggregating manifest...")
    
    all_images_map = {}
    source_counts = {}
    
    # Load all produced JSONs
    files = glob.glob("data/*_manifest.json")
    for fpath in files:
        if "staging" in fpath: continue # Skip old pilot
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
    with open("data/master_manifest.json", "w") as f:
        json.dump(all_images, f, indent=2)
        
    print("\nSUMMARY:")
    print("-" * 30)
    for source, count in source_counts.items():
        print(f"{source:<15}: {count} images")
    print("-" * 30)
    print(f"Total Unique:    {len(all_images)}")
    print("-" * 30)
    
    # Update data.js logic
    with open("data/images.js", "w") as f:
        f.write(f"const images = {json.dumps(all_images, indent=2)};")

if __name__ == "__main__":
    run()
