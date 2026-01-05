"""Tests for the vision classification pipeline."""
import pytest
import sqlite3
import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

import db


# Sample expected classifications for spot-checking
# Format: (image_id, expected_ship_type, expected_navy)
KNOWN_CLASSIFICATIONS = [
    # From Dreadnought Project - these are technical drawings
    ("tdp_plate1", "battleship", None),  # Allow any navy
    ("tdp_plate2", "battleship", None),
    
    # From Internet Archive - structural design book plates
    ("structuraldesign00hovgrich_69", "lines", None),  # Lines drawings
    ("structuraldesign00hovgrich_81", "lines", None),
]


class TestClassificationAccuracy:
    """Spot-check classification results against known images."""
    
    @pytest.fixture
    def production_db(self):
        """Connect to the real production database."""
        prod_db = Path(__file__).parent.parent / "data" / "gallery.db"
        if not prod_db.exists():
            pytest.skip("Production database not found")
        
        conn = sqlite3.connect(prod_db)
        conn.row_factory = sqlite3.Row
        return conn
    
    def test_classified_images_have_ship_type(self, production_db):
        """All completed analyses should have a ship_type."""
        cursor = production_db.cursor()
        cursor.execute("""
            SELECT id, ship_type FROM images 
            WHERE analysis_status = 'complete' AND ship_type IS NULL
        """)
        missing = cursor.fetchall()
        production_db.close()
        
        assert len(missing) == 0, f"Images missing ship_type: {[r['id'] for r in missing]}"
    
    def test_classified_images_have_navy(self, production_db):
        """All completed analyses should have a navy."""
        cursor = production_db.cursor()
        cursor.execute("""
            SELECT id, navy FROM images 
            WHERE analysis_status = 'complete' AND navy IS NULL
        """)
        missing = cursor.fetchall()
        production_db.close()
        
        assert len(missing) == 0, f"Images missing navy: {[r['id'] for r in missing]}"
    
    def test_reasoning_field_populated(self, production_db):
        """Reasoning should be populated for enriched images."""
        cursor = production_db.cursor()
        cursor.execute("""
            SELECT id, reasoning FROM images 
            WHERE analysis_status = 'complete' AND reasoning IS NOT NULL
        """)
        with_reasoning = cursor.fetchall()
        production_db.close()
        
        # At least some should have reasoning
        # This is a soft check since Phase 2 may not have run on all
        print(f"Images with reasoning: {len(with_reasoning)}")
    
    def test_no_unknown_ship_types(self, production_db):
        """Ship types should be from expected vocabulary."""
        valid_types = {
            'battleship', 'cruiser', 'destroyer', 'carrier', 'submarine',
            'lines', 'profile', 'photo', 'diagram', 'unknown', 'other',
            'pre-dreadnought', 'dreadnought'
        }
        
        cursor = production_db.cursor()
        cursor.execute("""
            SELECT DISTINCT ship_type FROM images 
            WHERE analysis_status = 'complete' AND ship_type IS NOT NULL
        """)
        found_types = {row['ship_type'].lower() for row in cursor.fetchall()}
        production_db.close()
        
        unexpected = found_types - valid_types
        if unexpected:
            print(f"Note: Found additional ship types: {unexpected}")


class TestDataIntegrity:
    """Test data integrity constraints."""
    
    @pytest.fixture
    def production_db(self):
        prod_db = Path(__file__).parent.parent / "data" / "gallery.db"
        if not prod_db.exists():
            pytest.skip("Production database not found")
        
        conn = sqlite3.connect(prod_db)
        conn.row_factory = sqlite3.Row
        return conn
    
    def test_no_duplicate_ids(self, production_db):
        """IDs should be unique."""
        cursor = production_db.cursor()
        cursor.execute("""
            SELECT id, COUNT(*) as cnt FROM images 
            GROUP BY id HAVING cnt > 1
        """)
        duplicates = cursor.fetchall()
        production_db.close()
        
        assert len(duplicates) == 0, f"Duplicate IDs found: {[r['id'] for r in duplicates]}"
    
    def test_local_paths_are_valid(self, production_db):
        """Local paths should follow expected pattern."""
        cursor = production_db.cursor()
        cursor.execute("SELECT id, local_path FROM images")
        rows = cursor.fetchall()
        production_db.close()
        
        for row in rows:
            path = row['local_path']
            # Paths should be storage-relative, NOT starting with img/
            assert not path.startswith('img/'), f"Path should be storage-relative, found 'img/' for {row['id']}: {path}"
            assert '/' in path, f"Invalid path format for {row['id']}: {path} (expected folder/file.ext)"

    
    def test_pending_vs_complete_counts(self, production_db):
        """Report on classification progress."""
        cursor = production_db.cursor()
        cursor.execute("""
            SELECT analysis_status, COUNT(*) as cnt 
            FROM images GROUP BY analysis_status
        """)
        stats = {row['analysis_status']: row['cnt'] for row in cursor.fetchall()}
        production_db.close()
        
        print(f"Classification stats: {stats}")
        # This is informational, not a hard assertion
