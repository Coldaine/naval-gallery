"""
Naval Gallery Configuration

Image storage is external to the git repository (e.g., Google Drive).

Auto-detection: The config will automatically look for common Google Drive
mount points. You can override by setting NAVAL_GALLERY_IMAGE_DIR.

Priority:
1. NAVAL_GALLERY_IMAGE_DIR environment variable (if set)
2. Auto-detected Google Drive path + /NavalGallery subfolder
3. Error with helpful instructions
"""

import os
import sys
from pathlib import Path
from typing import Optional

# ============================================================================
# AUTO-DETECTION CONFIGURATION
# ============================================================================

# Common Google Drive mount point patterns (relative to home directory)
# These are checked in order - first match wins
GOOGLE_DRIVE_PATTERNS = [
    "GoogleDrive",           # rclone default
    "Google Drive",          # GNOME/Nautilus
    "google-drive",          # Some Linux naming
    ".google-drive",         # Hidden mount
]

# Subfolder within Google Drive or project root for Naval Gallery images
NAVAL_GALLERY_SUBFOLDER = "img"


def _find_google_drive() -> Optional[Path]:
    """
    Auto-detect Google Drive mount point.
    
    Checks common mount locations relative to the user's home directory.
    Returns the first valid path found, or None if not detected.
    """
    home = Path.home()
    
    for pattern in GOOGLE_DRIVE_PATTERNS:
        candidate = home / pattern
        if candidate.exists() and candidate.is_dir():
            return candidate
    
    # Also check GVFS mounts (GNOME virtual filesystem)
    gvfs_path = Path(f"/run/user/{os.getuid()}/gvfs")
    if gvfs_path.exists():
        for item in gvfs_path.iterdir():
            if "google" in item.name.lower():
                return item
    
    return None


def _get_or_create_naval_gallery_dir(google_drive: Path) -> Path:
    """
    Get or create the NavalGallery subfolder within Google Drive.
    """
    naval_dir = google_drive / NAVAL_GALLERY_SUBFOLDER
    if not naval_dir.exists():
        print(f"[*] Creating Naval Gallery directory: {naval_dir}")
        naval_dir.mkdir(parents=True, exist_ok=True)
    return naval_dir


# ============================================================================
# IMAGE STORAGE CONFIGURATION
# ============================================================================

def get_image_dir() -> Path:
    """
    Get the configured image storage directory.
    
    Priority:
    1. NAVAL_GALLERY_IMAGE_DIR env var (explicit override)
    2. Auto-detected Google Drive
    
    In both cases, we append NAVAL_GALLERY_SUBFOLDER to the base path.
    """
    # Priority 1: Explicit environment variable
    image_dir_env = os.environ.get("NAVAL_GALLERY_IMAGE_DIR")
    
    if image_dir_env:
        base_path = Path(image_dir_env)
        if not base_path.exists():
            print(f"\nERROR: NAVAL_GALLERY_IMAGE_DIR base path does not exist: {base_path}\n")
            sys.exit(1)
        path = base_path / NAVAL_GALLERY_SUBFOLDER
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    # Priority 2: Auto-detect Google Drive
    google_drive = _find_google_drive()
    
    if google_drive:
        return _get_or_create_naval_gallery_dir(google_drive)
    
    # Priority 3: Error with instructions
    print("\n" + "=" * 70)
    print("ERROR: Image storage directory not configured!")
    print("=" * 70)
    print()
    print("Naval Gallery stores images externally (e.g., in Google Drive).")
    print()
    print("OPTION 1: Mount Google Drive")
    print("  The config will auto-detect these locations in your home directory:")
    for pattern in GOOGLE_DRIVE_PATTERNS:
        print(f"    ~/{pattern}/")
    print()
    print("OPTION 2: Set environment variable manually")
    print('  export NAVAL_GALLERY_IMAGE_DIR="/path/to/your/image/storage"')
    print()
    print("Add the export to ~/.bashrc or ~/.zshrc to persist it.")
    print("=" * 70 + "\n")
    sys.exit(1)


def get_staging_dir(source_name: str) -> Path:
    """
    Get a source-specific staging directory within the image storage.
    
    Args:
        source_name: Name of the source (e.g., 'ia', 'loc', 'wiki', 'dreadnought')
    
    Returns:
        Path to the staging directory (created if needed)
    """
    staging = get_image_dir() / source_name
    staging.mkdir(parents=True, exist_ok=True)
    return staging


def get_relative_path(source_name: str, filename: str) -> str:
    """
    Get the relative path for manifest entries.
    
    This returns a path relative to the image storage root,
    suitable for storing in manifests.
    """
    return f"{source_name}/{filename}"


def get_absolute_path(relative_path: str) -> Path:
    """
    Resolve a relative path (from manifest) to an absolute path in image storage.
    """
    return get_image_dir() / relative_path



# ============================================================================
# PROJECT PATHS (relative to git repo)
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
TOOLS_DIR = PROJECT_ROOT / "tools"


# ============================================================================
# VALIDATION ON IMPORT (optional check)
# ============================================================================

def validate_config():
    """Run validation - call this at script start to fail fast."""
    img_dir = get_image_dir()
    print(f"[*] Resolved image storage: {img_dir}")


if __name__ == "__main__":
    # Quick test
    validate_config()
    print(f"[*] Staging dir for 'test': {get_staging_dir('test')}")
