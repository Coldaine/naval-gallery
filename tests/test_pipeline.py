"""Integration tests for data pipeline contracts.

These tests verify that data flows correctly through the entire pipeline:
manifest → database → classification → frontend export.

The goal is to catch schema drift and field mapping errors before they
silently corrupt production data.
"""
import pytest
import sqlite3
import json
from pathlib import Path

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


class TestPipelineDataFlow:
    """Test that data flows correctly through all pipeline stages."""
    
    def test_manifest_to_db_preserves_all_manifest_fields(self, temp_db, tmp_path):
        """Manifest fields should survive import into database."""
        manifest_data = [
            {
                "id": "test_001",
                "local_path": "wiki/test_001.jpg",
                "url": "https://example.com/test.jpg",
                "source": "Wikimedia Commons",
                "title": "USS Test Ship Plan",
                "desc": "A test ship with unicode: 日本語",
                "date": "1942-01-15"
            }
        ]
        
        manifest = tmp_path / "data" / "test_manifest.json"
        manifest.write_text(json.dumps(manifest_data))
        
        db.import_manifest(manifest)
        
        # Verify all fields survived
        conn = sqlite3.connect(temp_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM images WHERE id = ?", ("test_001",))
        row = dict(cursor.fetchone())
        conn.close()
        
        assert row['local_path'] == "wiki/test_001.jpg"
        assert row['source'] == "Wikimedia Commons"
        assert row['title'] == "USS Test Ship Plan"
        assert "日本語" in row['desc']  # Unicode preserved
        assert row['analysis_status'] == "pending"
    
    def test_classification_to_db_preserves_all_broadside_fields(self, temp_db, tmp_path):
        """All BroadsideStudio-aligned fields should round-trip through save_analysis."""
        # Setup: import a test image
        manifest = tmp_path / "data" / "manifest.json"
        manifest.write_text(json.dumps([{"id": "broadside_test", "local_path": "test/img.jpg"}]))
        db.import_manifest(manifest)
        
        # Simulate a complete classification result with ALL schema fields
        full_result = {
            # Structure
            'image_type': 'single_view',
            'view_type': 'side_profile',
            'view_style': 'line_drawing_bw',
            'orientation': 'bow_left',
            'bounds': {'x': 10, 'y': 20, 'width': 800, 'height': 400},
            
            # Identification
            'ship_type': 'battleship',
            'ship_name': 'USS Arizona',
            'ship_class': 'Pennsylvania-class',
            'hull_number': 'BB-39',
            'navy': 'USN',
            'era': 'interwar',
            'is_historical': True,
            'designer': 'US Navy Bureau of Ships',
            
            # Quality
            'silhouette_clarity': 'clean',
            'annotation_density': 'light',
            'resolution_quality': 'high',
            'extraction_tier': 2,
            'suitable_for_extraction': True,
            'quality_issues': ['slight_yellowing'],
            
            # Text
            'text_content': [{'text': 'BB-39', 'location': {'x': 50, 'y': 10}}],
            
            # Metadata
            'reasoning': 'Identified by superstructure profile',
            'confidence': 0.95,
        }
        
        db.save_analysis("broadside_test", full_result)
        
        # Read back and verify every field
        conn = sqlite3.connect(temp_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM images WHERE id = ?", ("broadside_test",))
        row = dict(cursor.fetchone())
        conn.close()
        
        # Verify scalar fields
        assert row['image_type'] == 'single_view'
        assert row['view_type'] == 'side_profile'
        assert row['view_style'] == 'line_drawing_bw'
        assert row['orientation'] == 'bow_left'
        assert row['ship_type'] == 'battleship'
        assert row['ship_name'] == 'USS Arizona'
        assert row['extraction_tier'] == 2
        assert row['suitable_for_extraction'] == 1  # SQLite stores bool as int
        assert row['confidence'] == 0.95
        
        # Verify JSON fields are stored correctly
        bounds = json.loads(row['bounds'])
        assert bounds['width'] == 800
        
        text_content = json.loads(row['text_content'])
        assert text_content[0]['text'] == 'BB-39'
        
        quality_issues = json.loads(row['quality_issues'])
        assert 'slight_yellowing' in quality_issues
    
    def test_db_to_frontend_export_preserves_structure(self, temp_db, tmp_path):
        """Frontend export should match database structure."""
        # Setup: create and classify an image
        manifest = tmp_path / "data" / "manifest.json"
        manifest.write_text(json.dumps([{"id": "export_test", "local_path": "oni/export.jpg"}]))
        db.import_manifest(manifest)
        
        db.save_analysis("export_test", {
            'ship_type': 'cruiser',
            'view_type': 'plan_view',
            'extraction_tier': 3,
            'text_content': [{'text': 'CA-68', 'x': 100}]
        })
        
        # Export to frontend
        db.sync_frontend()
        
        # Parse the JS output
        js_file = tmp_path / "data" / "images.js"
        content = js_file.read_text()
        
        # Extract JSON from JS
        json_str = content.replace("const images = ", "").rstrip(";")
        data = json.loads(json_str)
        
        assert len(data) == 1
        entry = data[0]
        
        # Verify fields made it through
        assert entry['id'] == 'export_test'
        assert entry['ship_type'] == 'cruiser'
        assert entry['extraction_tier'] == 3
        
        # JSON fields should be parsed (not strings)
        assert isinstance(entry['text_content'], list)
        assert entry['text_content'][0]['text'] == 'CA-68'
    
    def test_full_pipeline_roundtrip(self, temp_db, tmp_path):
        """Complete manifest→classify→export pipeline should preserve all data."""
        # This is the integration test that catches schema drift
        
        # 1. Create realistic manifest
        manifest_data = [
            {"id": "pipe_1", "local_path": "wiki/pipe_1.svg", "title": "Test Plan A"},
            {"id": "pipe_2", "local_path": "oni/pipe_2.png", "title": "Test Plan B"},
        ]
        manifest = tmp_path / "data" / "manifest.json"
        manifest.write_text(json.dumps(manifest_data))
        
        # 2. Import
        db.import_manifest(manifest)
        
        # 3. Classify both
        for i, img_id in enumerate(["pipe_1", "pipe_2"], start=1):
            db.save_analysis(img_id, {
                'ship_type': 'battleship' if i == 1 else 'destroyer',
                'extraction_tier': i,
                'view_type': 'side_profile',
            })
        
        # 4. Export
        db.sync_frontend()
        
        # 5. Verify output
        js_file = tmp_path / "data" / "images.js"
        json_str = js_file.read_text().replace("const images = ", "").rstrip(";")
        data = json.loads(json_str)
        
        # Both entries should be present
        assert len(data) == 2
        ids = {d['id'] for d in data}
        assert ids == {'pipe_1', 'pipe_2'}
        
        # Original manifest data should persist
        for entry in data:
            assert entry['local_path'].endswith('.svg') or entry['local_path'].endswith('.png')
            assert 'Test Plan' in entry['title']
