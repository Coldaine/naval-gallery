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
                    'shipyard', 'hull_number', 'propulsion', 'armor', 'reasoning',
                    'image_type', 'view_style', 'orientation', 'extraction_tier',
                    'suitable_for_extraction', 'quality_issues', 'text_content'}
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
            'reasoning': 'Identified by turret arrangement',
            'view_style': 'line_drawing_bw',
            'extraction_tier': 2,
            'suitable_for_extraction': True,
            'text_content': [{'text': 'USS Arizona', 'location': {'x': 100, 'y': 20}}]
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
        assert row['view_style'] == 'line_drawing_bw'
        assert row['extraction_tier'] == 2
        assert json.loads(row['text_content'])[0]['text'] == 'USS Arizona'

    
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


class TestSyncFrontend:
    def test_exports_only_complete_images(self, temp_db, tmp_path):
        """Should only export images with 'complete' analysis status."""
        manifest = tmp_path / "data" / "test_manifest.json"
        manifest.write_text(json.dumps([
            {"id": "comp_1", "local_path": "img/c1.jpg"},
            {"id": "pend_1", "local_path": "img/p1.jpg"},
        ]))
        db.import_manifest(manifest)
        
        db.save_analysis("comp_1", {"ship_type": "battleship"})
        
        db.sync_frontend()
        
        output_file = tmp_path / "data" / "images.js"
        assert output_file.exists()
        
        content = output_file.read_text()
        assert "const images = [" in content
        
        # Parse the JSON part
        json_str = content.replace("const images = ", "").rstrip(";")
        data = json.loads(json_str)
        
        assert len(data) == 1
        assert data[0]['id'] == "comp_1"
        assert data[0]['analysis_status'] == "complete"

    def test_parses_json_fields_for_js(self, temp_db, tmp_path):
        """JSON fields in DB should be parsed into JS objects in export."""
        manifest = tmp_path / "data" / "test_manifest.json"
        manifest.write_text(json.dumps([
            {"id": "json_test", "local_path": "img/j.jpg"}
        ]))
        db.import_manifest(manifest)
        
        results = {
            'ship_type': 'cruiser',
            'text_content': [{'text': 'label', 'x': 10}],
            'bounds': {'x': 0, 'y': 0, 'w': 100, 'h': 50}
        }
        db.save_analysis("json_test", results)
        
        db.sync_frontend()
        
        json_str = (tmp_path / "data" / "images.js").read_text().replace("const images = ", "").rstrip(";")
        data = json.loads(json_str)
        
        assert isinstance(data[0]['text_content'], list)
        assert data[0]['text_content'][0]['text'] == 'label'
        assert isinstance(data[0]['bounds'], dict)
        assert data[0]['bounds']['w'] == 100

    def test_xss_protection_escapes_script_tags(self, temp_db, tmp_path):
        """Should escape </script> tags to prevent XSS."""
        manifest = tmp_path / "data" / "test_manifest.json"
        manifest.write_text(json.dumps([
            {"id": "xss_test", "local_path": "img/x.jpg"}
        ]))
        db.import_manifest(manifest)
        
        db.save_analysis("xss_test", {"ship_type": "</script><script>alert(1)</script>"})
        
        db.sync_frontend()
        
        content = (tmp_path / "data" / "images.js").read_text()
        assert "</script>" not in content
        assert "<\\/script>" in content

