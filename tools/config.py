"""
Naval Gallery Configuration

Image storage is external to the git repository (e.g., Google Drive).
Set the NAVAL_GALLERY_IMAGE_DIR environment variable to your storage path.

Example:
    export NAVAL_GALLERY_IMAGE_DIR="/home/coldaine/Google Drive/WarshipImages"
"""

import os
import sys
from pathlib import Path

# ============================================================================
# IMAGE STORAGE CONFIGURATION
# ============================================================================

def get_image_dir() -> Path:
    """
    Get the configured image storage directory.
    
    Raises:
        SystemExit: If NAVAL_GALLERY_IMAGE_DIR is not set or path doesn't exist.
    """
    image_dir = os.environ.get("NAVAL_GALLERY_IMAGE_DIR")
    
    if not image_dir:
        print("\n" + "=" * 70)
        print("ERROR: Image storage directory not configured!")
        print("=" * 70)
        print()
        print("Naval Gallery stores images externally (e.g., in Google Drive).")
        print("Please set the NAVAL_GALLERY_IMAGE_DIR environment variable:")
        print()
        print('    export NAVAL_GALLERY_IMAGE_DIR="/path/to/your/Google Drive/WarshipImages"')
        print()
        print("You can add this to your shell profile (~/.bashrc or ~/.zshrc).")
        print("=" * 70 + "\n")
        sys.exit(1)
    
    path = Path(image_dir)
    
    if not path.exists():
        print("\n" + "=" * 70)
        print("ERROR: Image storage directory does not exist!")
        print("=" * 70)
        print()
        print(f"Path: {path}")
        print()
        print("Please create this directory or update NAVAL_GALLERY_IMAGE_DIR.")
        print("=" * 70 + "\n")
        sys.exit(1)
    
    if not path.is_dir():
        print("\n" + "=" * 70)
        print("ERROR: NAVAL_GALLERY_IMAGE_DIR is not a directory!")
        print("=" * 70)
        print()
        print(f"Path: {path}")
        print("=" * 70 + "\n")
        sys.exit(1)
    
    return path


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
    get_image_dir()  # Will exit if not configured
    print(f"[*] Image storage: {get_image_dir()}")


if __name__ == "__main__":
    # Quick test
    validate_config()
    print(f"[*] Staging dir for 'test': {get_staging_dir('test')}")
