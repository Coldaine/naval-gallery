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
    
    for script in scripts:
        print(f"\n>>> Running {script}...")
        try:
            subprocess.run(["python", script], check=False) # Don't stop on single failure
        except Exception as e:
            print(f"Failed to run {script}: {e}")
            
    print("\n=== HARVEST COMPLETE ===")
    print("Aggregating manifest...")
    
    all_images = []
    
    # Load all produced JSONs
    files = glob.glob("data/*_manifest.json")
    for fpath in files:
        if "staging" in fpath: continue # Skip old pilot
        try:
            with open(fpath, "r") as f:
                data = json.load(f)
                all_images.extend(data)
        except:
            pass
            
    # Save master manifest
    with open("data/master_manifest.json", "w") as f:
        json.dump(all_images, f, indent=2)
        
    print(f"Total images collected: {len(all_images)}")
    
    # Update data.js logic - for now we just dump to a js file the frontend can load
    with open("data/images.js", "w") as f:
        f.write(f"const images = {json.dumps(all_images, indent=2)};")

if __name__ == "__main__":
    run()
