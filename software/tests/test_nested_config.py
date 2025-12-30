"""
Test nested configuration structure support.

Tests both nested and flat configuration formats.
"""

import unittest
import sys
import os
import json
import tempfile

# Import droplet_detection module (handling hyphenated directory)
import importlib.util  # noqa: E402

software_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
droplet_detection_path = os.path.join(software_dir, "droplet-detection")
if os.path.exists(droplet_detection_path):
    spec = importlib.util.spec_from_file_location(
        "droplet_detection", os.path.join(droplet_detection_path, "__init__.py")
    )
    droplet_detection = importlib.util.module_from_spec(spec)
    sys.modules["droplet_detection"] = droplet_detection
    spec.loader.exec_module(droplet_detection)

    DropletDetectionConfig = droplet_detection.DropletDetectionConfig
    load_config = droplet_detection.load_config
    save_config = droplet_detection.save_config
    extract_droplet_config = droplet_detection.extract_droplet_config
else:
    from droplet_detection import (
        DropletDetectionConfig,
        load_config,
        save_config,
        extract_droplet_config,
    )


class TestNestedConfig(unittest.TestCase):
    """Test nested configuration structure."""

    def test_extract_nested_config(self):
        """Test extracting config from nested structure."""
        nested_dict = {
            "modules": {"droplet_analysis": True, "other_module": False},
            "droplet_detection": {
                "histogram_window_size": 5000,
                "histogram_bins": 50,
                "min_area": 20,
            },
            "other_section": {"some_param": 123},
        }

        extracted = extract_droplet_config(nested_dict)

        self.assertEqual(extracted["histogram_window_size"], 5000)
        self.assertEqual(extracted["histogram_bins"], 50)
        self.assertEqual(extracted["min_area"], 20)
        self.assertNotIn("modules", extracted)
        self.assertNotIn("other_section", extracted)

    def test_extract_flat_config(self):
        """Test extracting config from flat structure."""
        flat_dict = {"histogram_window_size": 3000, "histogram_bins": 40, "min_area": 15}

        extracted = extract_droplet_config(flat_dict)

        self.assertEqual(extracted["histogram_window_size"], 3000)
        self.assertEqual(extracted["histogram_bins"], 40)
        self.assertEqual(extracted["min_area"], 15)

    def test_load_nested_config_file(self):
        """Test loading nested config from file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config_data = {
                "modules": {"droplet_analysis": True},
                "droplet_detection": {
                    "histogram_window_size": 4000,
                    "histogram_bins": 45,
                    "min_area": 25,
                },
            }
            json.dump(config_data, f)
            temp_path = f.name

        try:
            config = load_config(temp_path)

            self.assertEqual(config.histogram_window_size, 4000)
            self.assertEqual(config.histogram_bins, 45)
            self.assertEqual(config.min_area, 25)
        finally:
            os.unlink(temp_path)

    def test_load_flat_config_file(self):
        """Test loading flat config from file (backward compatibility)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config_data = {"histogram_window_size": 2000, "histogram_bins": 40, "min_area": 20}
            json.dump(config_data, f)
            temp_path = f.name

        try:
            config = load_config(temp_path)

            self.assertEqual(config.histogram_window_size, 2000)
            self.assertEqual(config.histogram_bins, 40)
            self.assertEqual(config.min_area, 20)
        finally:
            os.unlink(temp_path)

    def test_save_nested_config(self):
        """Test saving config in nested format."""
        config = DropletDetectionConfig({"histogram_window_size": 5000, "histogram_bins": 50})

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            save_config(config, temp_path, nested=True, include_modules=True)

            with open(temp_path, "r") as f:
                saved_data = json.load(f)

            self.assertIn("modules", saved_data)
            self.assertIn("droplet_analysis", saved_data["modules"])
            self.assertTrue(saved_data["modules"]["droplet_analysis"])
            self.assertIn("droplet_detection", saved_data)
            self.assertEqual(saved_data["droplet_detection"]["histogram_window_size"], 5000)
            self.assertEqual(saved_data["droplet_detection"]["histogram_bins"], 50)
        finally:
            os.unlink(temp_path)

    def test_save_flat_config(self):
        """Test saving config in flat format (backward compatible)."""
        config = DropletDetectionConfig({"histogram_window_size": 3000, "histogram_bins": 40})

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            save_config(config, temp_path, nested=False)

            with open(temp_path, "r") as f:
                saved_data = json.load(f)

            # Should be flat structure
            self.assertIn("histogram_window_size", saved_data)
            self.assertIn("histogram_bins", saved_data)
            self.assertNotIn("modules", saved_data)
            self.assertNotIn("droplet_detection", saved_data)
            self.assertEqual(saved_data["histogram_window_size"], 3000)
            self.assertEqual(saved_data["histogram_bins"], 40)
        finally:
            os.unlink(temp_path)

    def test_round_trip_nested(self):
        """Test round-trip: save nested, load nested."""
        original_config = DropletDetectionConfig(
            {"histogram_window_size": 6000, "histogram_bins": 60, "min_area": 30}
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            # Save in nested format
            save_config(original_config, temp_path, nested=True, include_modules=True)

            # Load back
            loaded_config = load_config(temp_path)

            self.assertEqual(loaded_config.histogram_window_size, 6000)
            self.assertEqual(loaded_config.histogram_bins, 60)
            self.assertEqual(loaded_config.min_area, 30)
        finally:
            os.unlink(temp_path)

    def test_round_trip_flat(self):
        """Test round-trip: save flat, load flat (backward compatibility)."""
        original_config = DropletDetectionConfig(
            {"histogram_window_size": 2000, "histogram_bins": 40}
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            # Save in flat format
            save_config(original_config, temp_path, nested=False)

            # Load back
            loaded_config = load_config(temp_path)

            self.assertEqual(loaded_config.histogram_window_size, 2000)
            self.assertEqual(loaded_config.histogram_bins, 40)
        finally:
            os.unlink(temp_path)

    def test_mixed_loading(self):
        """Test loading nested file and saving as flat (and vice versa)."""
        # Create nested file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            nested_data = {
                "modules": {"droplet_analysis": True},
                "droplet_detection": {"histogram_window_size": 4000, "histogram_bins": 50},
            }
            json.dump(nested_data, f)
            nested_path = f.name

        # Create separate flat file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            flat_data = {"histogram_window_size": 3000, "histogram_bins": 40}
            json.dump(flat_data, f)
            flat_path = f.name

        # Create output files
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            flat_output_path = f.name
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            nested_output_path = f.name

        try:
            # Load nested, save as flat
            config1 = load_config(nested_path)
            save_config(config1, flat_output_path, nested=False)

            # Load flat, save as nested
            config2 = load_config(flat_path)
            save_config(config2, nested_output_path, nested=True, include_modules=True)

            # Verify original configs
            self.assertEqual(config1.histogram_window_size, 4000)
            self.assertEqual(config2.histogram_window_size, 3000)

            # Verify saved files can be loaded
            loaded_flat = load_config(flat_output_path)
            loaded_nested = load_config(nested_output_path)

            self.assertEqual(loaded_flat.histogram_window_size, 4000)
            self.assertEqual(loaded_nested.histogram_window_size, 3000)
        finally:
            os.unlink(nested_path)
            os.unlink(flat_path)
            if os.path.exists(flat_output_path):
                os.unlink(flat_output_path)
            if os.path.exists(nested_output_path):
                os.unlink(nested_output_path)

    def test_extract_empty_dict(self):
        """Test extracting from empty or unknown structure."""
        empty_dict = {}
        extracted = extract_droplet_config(empty_dict)
        self.assertEqual(extracted, {})

        unknown_dict = {"unknown_section": {"param": 123}}
        extracted = extract_droplet_config(unknown_dict)
        self.assertEqual(extracted, {})


if __name__ == "__main__":
    unittest.main()
