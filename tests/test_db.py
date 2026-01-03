"""Tests for the database layer."""
import pytest
import sqlite3
import tempfile
import json
from pathlib import Path

# Adjust path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

import db


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Create a temporary database for testing."""
    test_db = tmp_path / "test_gallery.db"
    test_data_dir = tmp_path / "data"
    test_data_dir.mkdir()
    
    monkeypatch.setattr(db, "DB_PATH", test_db)
    monkeypatch.setattr(db, "DATA_DIR", test_data_dir)
    
    db.init_db()
    return test_db


class TestInitDb:
    def test_creates_database_file(self, temp_db):
        """Database file should be created on init."""
        assert temp_db.exists()
    
    def test_creates_images_table(self, temp_db):
        """Images table should exist with correct schema."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='images'")
        assert cursor.fetchone() is not None
        conn.close()
    
    def test_schema_has_required_columns(self, temp_db):
        """Schema should have all required columns."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(images)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()
        
        required = {'id', 'local_path', 'analysis_status', 'ship_type', 'navy', 
                    'shipyard', 'hull_number', 'propulsion', 'armor', 'reasoning'}
        assert required.issubset(columns)


class TestManifestImport:
    def test_imports_new_entries(self, temp_db, tmp_path, monkeypatch):
        """Should import new entries from manifest."""
        manifest = tmp_path / "data" / "test_manifest.json"
        manifest.write_text(json.dumps([
            {"id": "test_001", "local_path": "img/test.jpg", "title": "Test Ship"}
        ]))
        
        db.import_manifest(manifest)
        
        pending = db.get_pending()
        assert len(pending) == 1
        assert pending[0]['id'] == "test_001"
    
    def test_updates_existing_entries(self, temp_db, tmp_path):
        """Should update existing entries without duplicating."""
        manifest = tmp_path / "data" / "test_manifest.json"
        
        # First import
        manifest.write_text(json.dumps([
            {"id": "test_001", "local_path": "img/old.jpg", "title": "Old Title"}
        ]))
        db.import_manifest(manifest)
        
        # Second import with updated data
        manifest.write_text(json.dumps([
            {"id": "test_001", "local_path": "img/new.jpg", "title": "New Title"}
        ]))
        db.import_manifest(manifest)
        
        pending = db.get_pending()
        assert len(pending) == 1
        assert pending[0]['local_path'] == "img/new.jpg"


class TestGetPending:
    def test_returns_pending_images(self, temp_db, tmp_path):
        """Should return only images with pending status."""
        manifest = tmp_path / "data" / "test_manifest.json"
        manifest.write_text(json.dumps([
            {"id": "pending_1", "local_path": "img/p1.jpg"},
            {"id": "pending_2", "local_path": "img/p2.jpg"},
        ]))
        db.import_manifest(manifest)
        
        pending = db.get_pending()
        assert len(pending) == 2
    
    def test_limit_parameter(self, temp_db, tmp_path):
        """Limit parameter should restrict results."""
        manifest = tmp_path / "data" / "test_manifest.json"
        manifest.write_text(json.dumps([
            {"id": f"img_{i}", "local_path": f"img/{i}.jpg"} for i in range(10)
        ]))
        db.import_manifest(manifest)
        
        # This tests the parameterized LIMIT (SQLi fix)
        pending = db.get_pending(limit=3)
        assert len(pending) == 3


class TestSaveAnalysis:
    def test_saves_successful_analysis(self, temp_db, tmp_path):
        """Should save analysis results correctly."""
        manifest = tmp_path / "data" / "test_manifest.json"
        manifest.write_text(json.dumps([
            {"id": "test_ship", "local_path": "img/ship.jpg"}
        ]))
        db.import_manifest(manifest)
        
        results = {
            'ship_type': 'battleship',
            'navy': 'USN',
            'era': 'WWI',
            'shipyard': 'Brooklyn Navy Yard',
            'hull_number': 'BB-39',
            'reasoning': 'Identified by turret arrangement'
        }
        db.save_analysis("test_ship", results)
        
        conn = sqlite3.connect(temp_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM images WHERE id = ?", ("test_ship",))
        row = dict(cursor.fetchone())
        conn.close()
        
        assert row['analysis_status'] == 'complete'
        assert row['ship_type'] == 'battleship'
        assert row['shipyard'] == 'Brooklyn Navy Yard'
    
    def test_saves_error_state(self, temp_db, tmp_path):
        """Should save error state correctly."""
        manifest = tmp_path / "data" / "test_manifest.json"
        manifest.write_text(json.dumps([
            {"id": "broken_img", "local_path": "img/broken.jpg"}
        ]))
        db.import_manifest(manifest)
        
        db.save_analysis("broken_img", {}, error="API timeout")
        
        conn = sqlite3.connect(temp_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM images WHERE id = ?", ("broken_img",))
        row = dict(cursor.fetchone())
        conn.close()
        
        assert row['analysis_status'] == 'failed'
        assert row['error_message'] == "API timeout"
