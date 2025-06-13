"""
Tests for the file operations module.
"""

import os
import json
import tempfile
import unittest
from unittest.mock import patch, mock_open
from utils.file_operations import save_json_data, load_json_data, save_markdown

class TestFileOperationsModule(unittest.TestCase):
    """Tests for the file operations module."""

    def test_save_json_data(self):
        """Test the save_json_data function."""
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = os.path.join(temp_dir, "test_data.json")
            data = {"key": "value"}
            
            # Test saving data
            result = save_json_data(data, filepath)
            self.assertTrue(result)
            
            # Verify the file was created and contains the expected data
            self.assertTrue(os.path.exists(filepath))
            with open(filepath, "r") as f:
                saved_data = json.load(f)
            self.assertEqual(saved_data, data)
    
    def test_save_json_data_error(self):
        """Test the save_json_data function with an error."""
        with patch("builtins.open", side_effect=Exception("Test error")):
            result = save_json_data({"key": "value"}, "test.json")
            self.assertFalse(result)
    
    def test_load_json_data(self):
        """Test the load_json_data function."""
        # Create a temporary file with JSON data
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
            data = {"key": "value"}
            json.dump(data, temp_file)
            filepath = temp_file.name
        
        try:
            # Test loading data
            result = load_json_data(filepath)
            self.assertEqual(result, data)
        finally:
            # Clean up
            os.unlink(filepath)
    
    def test_load_json_data_file_not_found(self):
        """Test the load_json_data function when the file is not found."""
        result = load_json_data("nonexistent_file.json")
        self.assertIsNone(result)
    
    @patch("builtins.open", mock_open())
    @patch("json.load", side_effect=json.JSONDecodeError("Test error", "", 0))
    def test_load_json_data_json_error(self, mock_json_load):
        """Test the load_json_data function with a JSON error."""
        result = load_json_data("test.json")
        self.assertIsNone(result)
    
    def test_save_markdown(self):
        """Test the save_markdown function."""
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = os.path.join(temp_dir, "test.md")
            markdown_content = "# Test Markdown"
            
            # Test saving markdown
            result = save_markdown(markdown_content, filepath)
            self.assertTrue(result)
            
            # Verify the file was created and contains the expected content
            self.assertTrue(os.path.exists(filepath))
            with open(filepath, "r") as f:
                saved_content = f.read()
            self.assertEqual(saved_content, markdown_content)
    
    def test_save_markdown_error(self):
        """Test the save_markdown function with an error."""
        with patch("builtins.open", side_effect=Exception("Test error")):
            result = save_markdown("# Test", "test.md")
            self.assertFalse(result)

if __name__ == '__main__':
    unittest.main() 