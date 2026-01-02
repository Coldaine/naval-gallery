import json
import os
import glob

# Collates all harvester manifests into a single master_manifest.json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../"))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

def run():
    print("[*] Collating all manifests...")
    master = []
    
    manifest_files = glob.glob(os.path.join(DATA_DIR, "*_manifest.json"))
    
    for fpath in manifest_files:
        if "master_manifest.json" in fpath: continue
        
        print(f"    [+] Processing {os.path.basename(fpath)}")
        try:
            with open(fpath, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    master.extend(data)
                else:
                    print(f"    [!] Warning: {os.path.basename(fpath)} is not a list.")
        except Exception as e:
            print(f"    [!] Failed to read {fpath}: {e}")
            
    # Save master
    output_path = os.path.join(DATA_DIR, "master_manifest.json")
    with open(output_path, "w") as f:
        json.dump(master, f, indent=2)
        
    print(f"[*] Done. Master manifest contains {len(master)} items.")
    print(f"[*] Saved to: {output_path}")

if __name__ == "__main__":
    run()
