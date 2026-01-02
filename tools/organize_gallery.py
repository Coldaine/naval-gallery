#!/usr/bin/env python3
import os
import shutil
import argparse
import logging
from pathlib import Path
import db

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def sanitize(text):
    "Sanitize text for use in filenames/paths."
    if not text:
        return "Unknown"
    # Basic sanitization
    keep = (" ", ".", "_", "-")
    return "".join(c for c in text if c.isalnum() or c in keep).strip().replace(" ", "_")

def organize_images(limit=None, copy_only=False, dry_run=False):
    # 1. Get images ready to organize
    pending = db.get_ready_to_organize(limit=limit)
    if not pending:
        logger.info("[*] No images pending organization.")
        return

    logger.info(f"[*] Organizing {len(pending)} images.")
    
    base_dir = Path(__file__).parent.parent
    classified_base = base_dir / "img" / "classified"
    
    for item in pending:
        img_id = item['id']
        old_path = Path(item['local_path'])
        
        # Absolute path handling
        abs_old_path = base_dir / old_path if not old_path.is_absolute() else old_path
        
        if not abs_old_path.exists():
            logger.warning(f"[-] Original file not found: {abs_old_path}")
            db.update_organization(img_id, str(old_path), status='error')
            continue

        # 2. Construct New Path
        navy = sanitize(item['navy'])
        ship_type = sanitize(item['ship_type'])
        view_type = sanitize(item['view_type'])
        ship_name = sanitize(item['ship_name'])
        
        # img/classified/{navy}/{ship_type}/{view_type}/
        target_dir = classified_base / navy / ship_type / view_type
        
        # 3. Construct Filename
        # {navy}_{ship_name}_{view_type}_{id}.jpg
        ext = abs_old_path.suffix or ".jpg"
        new_filename = f"{navy}_{ship_name}_{view_type}_{img_id}{ext}"
        target_path = target_dir / new_filename
        
        # Relative path for DB storage (relative to project root)
        rel_target_path = target_path.relative_to(base_dir)

        if dry_run:
            logger.info(f"[DRY RUN] Would move {abs_old_path} -> {target_path}")
            continue

        # 4. Perform Action
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            
            if copy_only:
                shutil.copy2(abs_old_path, target_path)
                logger.info(f"[+] Copied: {img_id} to {rel_target_path}")
            else:
                shutil.move(abs_old_path, target_path)
                logger.info(f"[+] Moved: {img_id} to {rel_target_path}")
            
            # 5. Update DB
            db.update_organization(img_id, str(rel_target_path), status='organized')
            
        except Exception as e:
            logger.error(f"[!] Failed to organize {img_id}: {e}")
            db.update_organization(img_id, str(old_path), status='error')

def main():
    parser = argparse.ArgumentParser(description="Naval Gallery Image Organizer")
    parser.add_argument("--limit", type=int, default=None, help="Max images to organize")
    parser.add_argument("--copy", action="store_true", help="Copy instead of move")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen")
    
    args = parser.parse_args()
    
    organize_images(limit=args.limit, copy_only=args.copy, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
