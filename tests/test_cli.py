import json
import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from treeson import dir_to_json, github_repo_to_json, TreesonConfig, DEFAULT_IGNORES

@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory structure for testing."""
    (tmp_path / "file1.txt").write_text("content1")
    (tmp_path / "file2.log").write_text("content2")
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "file3.txt").write_text("content3")
    (tmp_path / "subdir" / "nested").mkdir()
    (tmp_path / "subdir" / "nested" / "file4.txt").write_text("content4")
    (tmp_path / ".hidden").write_text("hidden")
    (tmp_path / "treeson.egg-info").mkdir()
    (tmp_path / "treeson.egg-info" / "PKG-INFO").write_text("metadata")
    return tmp_path

def test_config_should_ignore():
    config = TreesonConfig(ignores={".git", "*.log", "temp_*"})
    
    assert config.should_ignore(".git") is True
    assert config.should_ignore("test.log") is True
    assert config.should_ignore("temp_file") is True
    assert config.should_ignore("regular.txt") is False
    assert config.should_ignore(".hidden") is True  # Default include_hidden=False
    
    config_hidden = TreesonConfig(include_hidden=True)
    assert config_hidden.should_ignore(".hidden") is False

def test_dir_to_json_basic(temp_dir):
    config = TreesonConfig(ignores=set())
    result = dir_to_json(temp_dir, config)
    
    assert "file1.txt" in result["files"]
    assert "file2.log" in result["files"]
    assert "subdir" in result
    assert "file3.txt" in result["subdir"]["files"]
    assert "nested" in result["subdir"]
    assert "file4.txt" in result["subdir"]["nested"]["files"]

def test_dir_to_json_glob_ignores(temp_dir):
    # DEFAULT_IGNORES includes *.egg-info
    config = TreesonConfig()
    result = dir_to_json(temp_dir, config)
    
    assert "treeson.egg-info" not in result
    assert "file2.log" in result["files"]
    
    # Custom glob ignore
    config_custom = TreesonConfig(ignores={"*.log"})
    result_custom = dir_to_json(temp_dir, config_custom)
    assert "file2.log" not in result_custom["files"]

def test_dir_to_json_max_depth(temp_dir):
    config = TreesonConfig(max_depth=1)
    result = dir_to_json(temp_dir, config)
    
    assert "file1.txt" in result["files"]
    assert "subdir" in result
    assert "files" in result["subdir"]
    assert not result["subdir"]["files"]  # Empty because depth reached
    assert "nested" not in result["subdir"]

def test_github_repo_to_json_mocked():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "tree": [
            {"path": "README.md", "type": "blob"},
            {"path": "src", "type": "tree"},
            {"path": "src/main.py", "type": "blob"},
            {"path": "src/utils", "type": "tree"},
            {"path": "src/utils/helper.py", "type": "blob"},
            {"path": "tests", "type": "tree"},
            {"path": "tests/test_main.py", "type": "blob"},
            {"path": "docs/index.md", "type": "blob"},
        ]
    }
    
    with patch("requests.get", return_value=mock_resp):
        # Test basic
        config = TreesonConfig(ignores=set())
        result = github_repo_to_json("https://github.com/user/repo", config)
        
        assert "README.md" in result["files"]
        assert "src" in result
        assert "main.py" in result["src"]["files"]
        assert "utils" in result["src"]
        assert "helper.py" in result["src"]["utils"]["files"]

        # Test max_depth
        config_depth = TreesonConfig(max_depth=1)
        result_depth = github_repo_to_json("https://github.com/user/repo", config_depth)
        
        assert "README.md" in result_depth["files"]
        assert "src" in result_depth
        assert "files" in result_depth["src"]
        assert not result_depth["src"]["files"]
        assert "utils" not in result_depth["src"]

        # Test ignores
        config_ignore = TreesonConfig(ignores={"src"})
        result_ignore = github_repo_to_json("https://github.com/user/repo", config_ignore)
        assert "src" not in result_ignore
        assert "README.md" in result_ignore["files"]
