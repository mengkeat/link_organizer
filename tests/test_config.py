"""
Tests for Config module
"""

import pytest
from pathlib import Path
from src.config import (
    Config,
    ClassificationConfig,
    CrawlerConfigSettings,
    get_config,
)


class TestClassificationConfig:
    """Test ClassificationConfig dataclass"""

    def test_default_categories(self):
        """Test default categories are populated"""
        config = ClassificationConfig()

        assert len(config.categories) > 0
        assert "Technology" in config.categories
        assert "AI/ML" in config.categories

    def test_default_content_types(self):
        """Test default content types are populated"""
        config = ClassificationConfig()

        assert len(config.content_types) > 0
        assert "tutorial" in config.content_types
        assert "research_paper" in config.content_types

    def test_custom_categories(self):
        """Test custom categories can be set"""
        config = ClassificationConfig(categories=["Custom1", "Custom2"])

        assert config.categories == ["Custom1", "Custom2"]


class TestCrawlerConfigSettings:
    """Test CrawlerConfigSettings dataclass"""

    def test_default_values(self):
        """Test default crawler settings"""
        config = CrawlerConfigSettings()

        assert config.data_dir == "dat"
        assert config.index_file == "index.json"
        assert config.classifications_file == "classifications.json"
        assert config.max_retries == 3
        assert config.classification_workers == 5
        assert config.fetch_workers == 5
        assert config.request_delay == 1.0
        assert config.enable_tui is False

    def test_custom_values(self):
        """Test custom crawler settings"""
        config = CrawlerConfigSettings(
            data_dir="custom_dir",
            max_retries=5,
            enable_tui=True,
        )

        assert config.data_dir == "custom_dir"
        assert config.max_retries == 5
        assert config.enable_tui is True


class TestConfig:
    """Test Config class"""

    def setup_method(self):
        """Reset singleton before each test"""
        Config.reset_instance()

    def teardown_method(self):
        """Reset singleton after each test"""
        Config.reset_instance()

    def test_default_config(self):
        """Test creating config with defaults"""
        config = Config()

        assert isinstance(config.classification, ClassificationConfig)
        assert isinstance(config.crawler, CrawlerConfigSettings)
        assert config.default_input_file == "links.md"

    def test_load_nonexistent_file(self, tmp_path):
        """Test loading from non-existent file returns defaults"""
        config = Config.load(tmp_path / "nonexistent.yaml")

        assert config.default_input_file == "links.md"
        assert config.crawler.data_dir == "dat"

    def test_load_from_yaml(self, tmp_path):
        """Test loading config from YAML file"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
default_input_file: custom_links.md
crawler:
  data_dir: custom_dat
  max_retries: 5
  fetch_workers: 10
classification:
  categories:
    - CustomCat1
    - CustomCat2
"""
        )

        config = Config.load(config_file)

        assert config.default_input_file == "custom_links.md"
        assert config.crawler.data_dir == "custom_dat"
        assert config.crawler.max_retries == 5
        assert config.crawler.fetch_workers == 10
        assert config.classification.categories == ["CustomCat1", "CustomCat2"]

    def test_load_partial_yaml(self, tmp_path):
        """Test loading YAML with only some settings"""
        config_file = tmp_path / "partial.yaml"
        config_file.write_text(
            """
crawler:
  max_retries: 10
"""
        )

        config = Config.load(config_file)

        assert config.crawler.max_retries == 10
        assert config.crawler.data_dir == "dat"
        assert config.default_input_file == "links.md"

    def test_load_empty_yaml(self, tmp_path):
        """Test loading empty YAML file returns defaults"""
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")

        config = Config.load(config_file)

        assert config.default_input_file == "links.md"
        assert config.crawler.data_dir == "dat"

    def test_load_yaml_with_null_values(self, tmp_path):
        """Test loading YAML with null values"""
        config_file = tmp_path / "null.yaml"
        config_file.write_text(
            """
crawler:
  data_dir: null
"""
        )

        config = Config.load(config_file)
        assert config.crawler.data_dir is None


class TestConfigSingleton:
    """Test Config singleton pattern"""

    def setup_method(self):
        """Reset singleton before each test"""
        Config.reset_instance()

    def teardown_method(self):
        """Reset singleton after each test"""
        Config.reset_instance()

    def test_get_instance_returns_same_object(self):
        """Test get_instance returns same object on multiple calls"""
        instance1 = Config.get_instance()
        instance2 = Config.get_instance()

        assert instance1 is instance2

    def test_get_instance_uses_first_path(self, tmp_path):
        """Test get_instance only uses config_path on first call"""
        config1 = tmp_path / "config1.yaml"
        config1.write_text("default_input_file: first.md")

        config2 = tmp_path / "config2.yaml"
        config2.write_text("default_input_file: second.md")

        instance1 = Config.get_instance(config1)
        instance2 = Config.get_instance(config2)

        assert instance1.default_input_file == "first.md"
        assert instance2.default_input_file == "first.md"

    def test_reset_instance(self, tmp_path):
        """Test reset_instance clears the singleton"""
        config1 = tmp_path / "config1.yaml"
        config1.write_text("default_input_file: first.md")

        config2 = tmp_path / "config2.yaml"
        config2.write_text("default_input_file: second.md")

        instance1 = Config.get_instance(config1)
        assert instance1.default_input_file == "first.md"

        Config.reset_instance()

        instance2 = Config.get_instance(config2)
        assert instance2.default_input_file == "second.md"

    def test_get_config_convenience_function(self):
        """Test get_config convenience function"""
        config = get_config()

        assert isinstance(config, Config)
        assert config is Config.get_instance()

    def test_get_config_with_path(self, tmp_path):
        """Test get_config with custom path"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("default_input_file: custom.md")

        config = get_config(config_file)

        assert config.default_input_file == "custom.md"


class TestConfigFromDict:
    """Test Config._from_dict() method"""

    def test_from_empty_dict(self):
        """Test creating config from empty dict"""
        config = Config._from_dict({})

        assert config.default_input_file == "links.md"
        assert config.crawler.data_dir == "dat"

    def test_from_full_dict(self):
        """Test creating config from complete dict"""
        data = {
            "default_input_file": "my_links.md",
            "crawler": {
                "data_dir": "my_data",
                "index_file": "my_index.json",
                "classifications_file": "my_class.json",
                "max_retries": 5,
                "classification_workers": 10,
                "fetch_workers": 8,
                "request_delay": 2.0,
                "enable_tui": True,
            },
            "classification": {
                "categories": ["Cat1", "Cat2"],
                "content_types": ["type1", "type2"],
            },
        }

        config = Config._from_dict(data)

        assert config.default_input_file == "my_links.md"
        assert config.crawler.data_dir == "my_data"
        assert config.crawler.max_retries == 5
        assert config.crawler.enable_tui is True
        assert config.classification.categories == ["Cat1", "Cat2"]
        assert config.classification.content_types == ["type1", "type2"]

    def test_from_dict_ignores_unknown_keys(self):
        """Test that unknown keys in dict are ignored"""
        data = {
            "unknown_key": "value",
            "crawler": {
                "unknown_crawler_key": "value",
                "max_retries": 7,
            },
        }

        config = Config._from_dict(data)

        assert config.crawler.max_retries == 7
        assert not hasattr(config, "unknown_key")
