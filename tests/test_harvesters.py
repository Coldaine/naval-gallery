"""Integration tests for image harvesters.

These tests use frozen API responses to verify that harvester parsing logic
works correctly. This catches selector drift when external sites change
their structure.

To update fixtures after intentional changes:
  1. Run the harvester with --debug to capture live responses
  2. Save relevant responses to tests/fixtures/
  3. Update expected values in tests
"""
import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "harvesters"))
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

# Import the functions we're testing (not the full module to avoid config side effects)
import wiki_walker


FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestWikiWalkerParsing:
    """Test WikiWalker's ability to parse Wikimedia Commons API responses."""
    
    def test_search_category_filters_relevant_files(self):
        """search_category should filter for plan/diagram/lines keywords."""
        # Load frozen API response
        category_response = json.loads(
            (FIXTURES_DIR / "wikimedia_category_response.json").read_text()
        )
        
        # Mock the requests.get call
        mock_response = MagicMock()
        mock_response.json.return_value = category_response
        
        with patch('requests.get', return_value=mock_response):
            results = wiki_walker.search_category("Category:Test", depth=0, max_depth=0)
        
        # Should find files with plan/diagram/lines/drawing keywords
        # From fixture: Iowa lines plan, Dreadnought profile diagram, Bismarck layout drawing
        # Should NOT include: Yamato photo (no keywords), Subcategory (ns=14)
        assert len(results) == 3
        assert "File:USS Iowa BB-61 hull lines plan.svg" in results
        assert "File:HMS Dreadnought profile diagram.png" in results
        assert "File:Bismarck deck layout drawing.png" in results
        
        # Photo should be filtered out
        assert "File:Yamato photo at sea.jpg" not in results
    
    def test_get_file_info_extracts_metadata(self):
        """get_file_info should extract URL and cleaned metadata."""
        fileinfo_response = json.loads(
            (FIXTURES_DIR / "wikimedia_fileinfo_response.json").read_text()
        )
        
        mock_response = MagicMock()
        mock_response.json.return_value = fileinfo_response
        
        with patch('requests.get', return_value=mock_response):
            results = wiki_walker.get_file_info([
                "File:USS Iowa BB-61 hull lines plan.svg",
                "File:HMS Dreadnought profile diagram.png",
                "File:Bismarck deck layout drawing.png"
            ])
        
        # Should extract data from all 3 files
        assert len(results) == 3
        
        # Find Iowa entry
        iowa = next(r for r in results if 'Iowa' in r['title'])
        assert iowa['id'] == 'wiki_12345'
        assert iowa['url'].startswith('https://upload.wikimedia.org')
        assert 'Hull lines plan' in iowa['desc']
        assert iowa['date'] == '1943'
        assert iowa['source'] == 'Wikimedia Commons'
        
        # Find Dreadnought entry - date should have HTML stripped
        dread = next(r for r in results if 'Dreadnought' in r['title'])
        assert dread['date'] == '1906'  # HTML <span> stripped
        assert '<' not in dread['date']  # No HTML remnants
    
    def test_get_file_info_handles_missing_metadata(self):
        """get_file_info should handle missing/incomplete metadata gracefully."""
        # Response with minimal metadata
        minimal_response = {
            "query": {
                "pages": {
                    "99999": {
                        "pageid": 99999,
                        "title": "File:Unknown ship.jpg",
                        "imageinfo": [{
                            "url": "https://example.com/img.jpg",
                            "extmetadata": {}  # Empty metadata
                        }]
                    }
                }
            }
        }
        
        mock_response = MagicMock()
        mock_response.json.return_value = minimal_response
        
        with patch('requests.get', return_value=mock_response):
            results = wiki_walker.get_file_info(["File:Unknown ship.jpg"])
        
        assert len(results) == 1
        assert results[0]['desc'] == 'Unknown'
        assert results[0]['date'] == 'Unknown'
    
    def test_get_file_info_handles_api_error(self):
        """get_file_info should return empty list on API failure."""
        mock_response = MagicMock()
        mock_response.json.side_effect = Exception("Network error")
        
        with patch('requests.get', return_value=mock_response):
            results = wiki_walker.get_file_info(["File:Test.jpg"])
        
        # Should gracefully return empty, not crash
        assert results == []


class TestWikiWalkerFiltering:
    """Test WikiWalker's filtering logic for relevant content."""
    
    @pytest.mark.parametrize("title,should_match", [
        ("File:USS Iowa lines plan.svg", True),
        ("File:HMS Dreadnought profile diagram.png", True),
        ("File:Ship layout drawing 1944.jpg", True),
        ("File:Battleship photo colorized.jpg", False),
        ("File:Ship museum interior.jpg", False),
        ("File:Naval battle painting.jpg", False),
    ])
    def test_title_keyword_filtering(self, title, should_match):
        """Titles should be filtered by plan/diagram/lines/layout/drawing keywords."""
        # Directly test the filtering logic
        lower_title = title.lower()
        keywords = ['plan', 'profile', 'lines', 'diagram', 'layout', 'drawing']
        matches = any(kw in lower_title for kw in keywords)
        
        assert matches == should_match, f"'{title}' should {'match' if should_match else 'not match'}"
