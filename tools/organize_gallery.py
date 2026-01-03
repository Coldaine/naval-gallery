#!/usr/bin/env python3
import os
import shutil
import argparse
import logging
import sys
from pathlib import Path

# Add to path for config import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_image_dir, validate_config
import db

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def sanitize(text, length=30):
    """
    Sanitize text for use in filenames and directory paths.
    
    Removes potentially dangerous characters (like dots and slashes) to prevent
    Path Traversal vulnerabilities. Truncates long segments to ensure filesystem
    compatibility.
    
    Args:
        text (str): The text to sanitize.
        length (int): Maximum length of the sanitized segment.
        
    Returns:
        str: A safe, filesystem-friendly string.
    """
    if not text:
        return "Unknown"
    
    # Strictly allow only alphanumeric, spaces, hyphens and underscores
    # Specifically remove '.' to prevent path traversal
    clean = "".join(c for c in text if c.isalnum() or c in (" ", "_", "-")).strip()
    clean = clean.replace(" ", "_")
    
    # Truncate and strip trailing underscores
    return clean[:length].rstrip("_")

def organize_images(limit=None, copy_only=False, dry_run=False):
    """
    Orchestrates the physical organization of classified images.
    
    Fetches successfully analyzed images from the database and moves or copies
    them into a structured directory hierarchy based on their metadata.
    
    Args:
        limit (int, optional): Maximum number of images to process.
        copy_only (bool): If True, copy files instead of moving them.
        dry_run (bool): If True, log intended actions without modifying the disk.
    """
    # 1. Get images ready to organize
    pending = db.get_ready_to_organize(limit=limit)
    if not pending:
        logger.info("[*] No images pending organization.")
        return

    logger.info(f"[*] Organizing {len(pending)} images.")
    
    image_dir = get_image_dir()
    classified_base = image_dir / "classified"
    
    for item in pending:
        img_id = item['id']
        old_path_str = item.get('local_path')
        if not old_path_str:
            logger.warning(f"[-] No local path for image {img_id}")
            db.update_organization(img_id, "Unknown", status='error')
            continue
            
        old_path = Path(old_path_str)
        
        # Paths in DB might be relative to image_dir or absolute
        if old_path.is_absolute():
            abs_old_path = old_path
        else:
            # Handle both 'img/source/file.jpg' and 'source/file.jpg'
            if str(old_path).startswith("img/"):
                # If it has img/ prefix, it's relative to the PARENT of image_dir (usually PROJECT_ROOT if local)
                # But if image_dir is external, 'img/' is likely inside it.
                # The most robust way is to check both.
                abs_old_path = image_dir / old_path
                if not abs_old_path.exists():
                    # Strip 'img/' and try again
                    abs_old_path = image_dir / Path(*old_path.parts[1:])
            else:
                abs_old_path = image_dir / old_path
        
        if not abs_old_path.exists():
            logger.warning(f"[-] Original file not found: {abs_old_path}")
            db.update_organization(img_id, str(old_path), status='error')
            continue

        # 2. Construct New Path with robust sanitization
        navy = sanitize(item.get('navy', 'Unknown'))
        ship_type = sanitize(item.get('ship_type', 'Unknown'))
        view_type = sanitize(item.get('view_type', 'Unknown'))
        ship_name = sanitize(item.get('ship_name', 'Unknown'))
        
        # classified/{navy}/{ship_type}/{view_type}/
        target_dir = classified_base / navy / ship_type / view_type
        
        # 3. Construct Filename
        # {navy}_{ship_name}_{view_type}_{id}.jpg
        ext = abs_old_path.suffix or ".jpg"
        new_filename = f"{navy}_{ship_name}_{view_type}_{img_id}{ext}"
        target_path = target_dir / new_filename
        
        # Relative path for DB storage (relative to image_dir)
        rel_target_path = f"classified/{navy}/{ship_type}/{view_type}/{new_filename}"

        if dry_run:
            logger.info(f"[DRY RUN] Would move {abs_old_path} -> {target_path}")
            continue

        # 4. Perform Action
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            
            if copy_only:
                shutil.copy2(abs_old_path, target_path)
                logger.info(f"[+] Copied: {img_id} to img/{rel_target_path}")
            else:
                shutil.move(abs_old_path, target_path)
                logger.info(f"[+] Moved: {img_id} to img/{rel_target_path}")
            
            # 5. Update DB
            db.update_organization(img_id, rel_target_path, status='organized')
            
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
