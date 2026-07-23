import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from osw_sanitizer import (
    DatasetValidationError,
    OSWSanitization,
    SanitizationConfig,
    SanitizationProcessor,
    SanitizationResult,
)


ASSETS_DIR = Path(__file__).parent / "assets"


class TestOSWSanitization(unittest.TestCase):
    def test_public_api_sanitizes_dataset_and_returns_result(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = os.path.join(temp_dir, "output")

            result = OSWSanitization(
                input_path=str(ASSETS_DIR / "precision_and_null_tags.zip"),
                output_dir=output_dir,
            ).sanitize()

            self.assertTrue(result.success)
            self.assertTrue(os.path.isfile(result.updated_dataset_zip))
            self.assertTrue(os.path.isfile(result.fixes_json))

            sanitized = self._read_geojson_from_zip(result.updated_dataset_zip, "edges.geojson")
            self.assertNotIn("width", sanitized["features"][0]["properties"])
            self.assertEqual(
                sanitized["features"][0]["geometry"]["coordinates"],
                [-122.1234567, 47.1234567],
            )

            with open(result.fixes_json, "r", encoding="utf-8") as fixes_file:
                fixes = json.load(fixes_file)
            self.assertEqual(fixes["files"][0]["removedTags"][0]["tag"], "width")
            self.assertEqual(len(fixes["files"][0]["precisionUpdates"]), 2)

    def test_sanitize_dataset_classmethod_returns_service_compatible_dict(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = os.path.join(temp_dir, "output")

            result = OSWSanitization.sanitize_dataset(
                str(ASSETS_DIR / "zero_length_edge.zip"),
                output_dir,
            )

            self.assertIsInstance(result, dict)
            self.assertTrue(result["success"])
            sanitized = self._read_geojson_from_zip(result["updated_dataset_zip"], "edges.geojson")
            self.assertEqual(sanitized["features"], [])

    def test_backward_compatible_processor_alias(self):
        self.assertIs(SanitizationProcessor, OSWSanitization)

    def test_allow_zero_length_lines_preserves_zero_length_edge(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = os.path.join(temp_dir, "output")

            result = OSWSanitization(
                input_path=str(ASSETS_DIR / "zero_length_edge.zip"),
                output_dir=output_dir,
                config=SanitizationConfig(allow_zero_length_lines=True),
            ).sanitize()

            sanitized = self._read_geojson_from_zip(result.updated_dataset_zip, "edges.geojson")
            self.assertEqual(len(sanitized["features"]), 1)

    def test_oversized_edge_is_split_and_generates_node(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = os.path.join(temp_dir, "output")

            result = OSWSanitization(
                input_path=str(ASSETS_DIR / "oversized_edge.zip"),
                output_dir=output_dir,
                config=SanitizationConfig(max_geometry_vertices=5),
            ).sanitize()

            edges = self._read_geojson_from_zip(result.updated_dataset_zip, "edges.geojson")
            nodes = self._read_geojson_from_zip(result.updated_dataset_zip, "nodes.geojson")
            self.assertEqual(len(edges["features"]), 2)
            self.assertEqual(edges["features"][0]["properties"]["_v_id"], "edge-large-split-node-1")
            self.assertEqual(edges["features"][1]["properties"]["_u_id"], "edge-large-split-node-1")
            self.assertEqual(nodes["features"][0]["properties"]["_id"], "edge-large-split-node-1")

    def test_unsupported_files_are_removed_and_logged(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = os.path.join(temp_dir, "output")

            result = OSWSanitization(
                input_path=str(ASSETS_DIR / "unsupported_files.zip"),
                output_dir=output_dir,
            ).sanitize()

            with zipfile.ZipFile(result.updated_dataset_zip, "r") as zip_file:
                self.assertNotIn("readme.txt", zip_file.namelist())
                self.assertNotIn("notes.geojson", zip_file.namelist())
            with open(result.fixes_json, "r", encoding="utf-8") as fixes_file:
                fixes = json.load(fixes_file)
            self.assertEqual(
                {entry["filename"] for entry in fixes["removedFiles"]},
                {"readme.txt", "notes.geojson"},
            )

    def test_config_validation_matches_validator_names(self):
        with self.assertRaises(TypeError):
            SanitizationConfig(max_geometry_vertices=True)
        with self.assertRaises(TypeError):
            SanitizationConfig(allow_zero_length_lines="yes")
        with self.assertRaises(TypeError):
            SanitizationConfig(coordinate_precision=True)
        with self.assertRaises(ValueError):
            SanitizationConfig(coordinate_precision=-1)
        with self.assertRaises(ValueError):
            SanitizationConfig(max_geometry_vertices=1)

    def test_constructor_rejects_invalid_config_type(self):
        with self.assertRaises(TypeError):
            OSWSanitization(config={})

    def test_result_to_dict(self):
        result = SanitizationResult(success=True, message="ok", updated_dataset_zip="out.zip", fixes_json="fixes.json")

        self.assertEqual(
            result.to_dict(),
            {
                "success": True,
                "message": "ok",
                "updated_dataset_zip": "out.zip",
                "fixes_json": "fixes.json",
            },
        )

    def test_missing_input_and_output_paths_fail_cleanly(self):
        missing_input = OSWSanitization(output_dir="/tmp/out").sanitize()
        missing_output = OSWSanitization(input_path=str(ASSETS_DIR / "zero_length_edge.zip")).sanitize()
        nonexistent = OSWSanitization(input_path="/missing/input.zip", output_dir="/tmp/out").sanitize()

        self.assertFalse(missing_input.success)
        self.assertIn("Input dataset path is missing", missing_input.message)
        self.assertFalse(missing_output.success)
        self.assertIn("Output directory path is missing", missing_output.message)
        self.assertFalse(nonexistent.success)
        self.assertIn("Input dataset not found", nonexistent.message)

    def test_nested_single_dataset_directory_is_flattened(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = OSWSanitization(
                input_path=str(ASSETS_DIR / "nested_dataset.zip"),
                output_dir=os.path.join(temp_dir, "output"),
            ).sanitize()

            self.assertTrue(result.success)
            with zipfile.ZipFile(result.updated_dataset_zip, "r") as zip_file:
                self.assertIn("edges.geojson", zip_file.namelist())

    def test_non_finite_coordinate_fails_with_located_message(self):
        payload = self._feature_collection(
            properties={"_id": "bad-coordinate"},
            coordinates=[float("inf"), 47.0],
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            input_zip = os.path.join(temp_dir, "bad.zip")
            self._write_zip(input_zip, {"edges.geojson": payload})

            result = OSWSanitization(input_path=input_zip, output_dir=os.path.join(temp_dir, "output")).sanitize()

            self.assertFalse(result.success)
            self.assertIn("edges.geojson", result.message)
            self.assertIn("Infinity", result.message)

    def test_non_finite_property_fails_with_located_message(self):
        payload = self._feature_collection(
            properties={"_id": "bad-property", "speed": float("inf")},
            coordinates=[-122.1, 47.1],
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            input_zip = os.path.join(temp_dir, "bad.zip")
            self._write_zip(input_zip, {"edges.geojson": payload})

            result = OSWSanitization(input_path=input_zip, output_dir=os.path.join(temp_dir, "output")).sanitize()

            self.assertFalse(result.success)
            self.assertIn("speed", result.message)
            self.assertIn("Infinity", result.message)

    def test_polygon_is_not_split(self):
        polygon = self._feature_collection(
            properties={"_id": "polygon-1"},
            coordinates=[self._line_coordinates(6) + [[0, 0]]],
            geometry_type="Polygon",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            input_zip = os.path.join(temp_dir, "polygon.zip")
            output_dir = os.path.join(temp_dir, "output")
            self._write_zip(input_zip, {"polygons.geojson": polygon})

            result = OSWSanitization(
                input_path=input_zip,
                output_dir=output_dir,
                config=SanitizationConfig(max_geometry_vertices=5),
            ).sanitize()

            sanitized = self._read_geojson_from_zip(result.updated_dataset_zip, "polygons.geojson")
            self.assertEqual(len(sanitized["features"]), 1)
            self.assertEqual(len(sanitized["features"][0]["geometry"]["coordinates"][0]), 7)

    def test_dataset_validation_error_type_is_exported(self):
        self.assertTrue(issubclass(DatasetValidationError, Exception))

    def test_macos_sidecar_files_are_skipped(self):
        payload = self._feature_collection(
            properties={"_id": "edge-1"},
            coordinates=[[-122.1, 47.1], [-122.2, 47.2]],
            geometry_type="LineString",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            input_zip = os.path.join(temp_dir, "macos.zip")
            output_dir = os.path.join(temp_dir, "output")
            self._write_zip(
                input_zip,
                {
                    "edges.geojson": payload,
                    ".DS_Store": "junk",
                    "._edges.geojson": "resource fork",
                    "__MACOSX/._edges.geojson": "resource fork",
                },
            )

            result = OSWSanitization(input_path=input_zip, output_dir=output_dir).sanitize()

            self.assertTrue(result.success)
            with zipfile.ZipFile(result.updated_dataset_zip, "r") as zip_file:
                names = zip_file.namelist()
            self.assertIn("edges.geojson", names)
            self.assertNotIn(".DS_Store", names)
            self.assertNotIn("._edges.geojson", names)
            self.assertNotIn("__MACOSX/._edges.geojson", names)

    def test_generated_split_nodes_are_appended_to_existing_nodes_file(self):
        edge = self._feature_collection(
            properties={"_id": "edge-large", "_u_id": "node-u", "_v_id": "node-v"},
            coordinates=self._line_coordinates(6),
            geometry_type="LineString",
        )
        nodes = self._feature_collection(
            properties={"_id": "node-u"},
            coordinates=[0, 0],
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            input_zip = os.path.join(temp_dir, "with-nodes.zip")
            output_dir = os.path.join(temp_dir, "output")
            self._write_zip(input_zip, {"edges.geojson": edge, "nodes.geojson": nodes})

            result = OSWSanitization(
                input_path=input_zip,
                output_dir=output_dir,
                config=SanitizationConfig(max_geometry_vertices=5),
            ).sanitize()

            sanitized_nodes = self._read_geojson_from_zip(result.updated_dataset_zip, "nodes.geojson")
            node_ids = [feature["properties"]["_id"] for feature in sanitized_nodes["features"]]
            self.assertEqual(node_ids, ["node-u", "edge-large-split-node-1"])

    def test_cp1252_encoded_geojson_uses_inmemory_fallback(self):
        payload = self._feature_collection(
            properties={"_id": "edge-1", "name": "Bench \u00a2"},
            coordinates=[-122.1234567, 47.1234567],
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            input_zip = os.path.join(temp_dir, "cp1252.zip")
            output_dir = os.path.join(temp_dir, "output")
            geojson_text = json.dumps(payload, ensure_ascii=False).encode("cp1252")
            with zipfile.ZipFile(input_zip, "w", zipfile.ZIP_DEFLATED) as zip_file:
                zip_file.writestr("edges.geojson", geojson_text)

            result = OSWSanitization(input_path=input_zip, output_dir=output_dir).sanitize()

            sanitized = self._read_geojson_from_zip(result.updated_dataset_zip, "edges.geojson")
            self.assertEqual(sanitized["features"][0]["properties"]["name"], "Bench \u00a2")

    def test_message_variants(self):
        no_change = {
            "removed_values": False,
            "precision_updates": False,
            "removed_edges": False,
            "split_edges": False,
            "removed_files": False,
        }
        precision = {**no_change, "precision_updates": True}
        removed = {**no_change, "removed_values": True}
        both = {**precision, "removed_values": True}
        compliance = {**no_change, "split_edges": True}

        self.assertEqual(
            OSWSanitization._build_message(no_change),
            "No changes were needed. The dataset is already clean.",
        )
        self.assertEqual(
            OSWSanitization._build_message(precision),
            "Coordinates were standardized for consistency.",
        )
        self.assertEqual(
            OSWSanitization._build_message(removed),
            "Invalid or empty values were removed from the dataset.",
        )
        self.assertEqual(
            OSWSanitization._build_message(both),
            "Dataset was cleaned and coordinates were standardized.",
        )
        self.assertEqual(
            OSWSanitization._build_message(compliance),
            "Dataset was sanitized for OSW compliance.",
        )

    def test_private_helpers_cover_edge_branches(self):
        self.assertEqual(OSWSanitization._line_length("bad"), 0.0)
        self.assertEqual(OSWSanitization._line_length([[0, 0], ["bad"], [1, 1]]), 0.0)
        self.assertEqual(OSWSanitization._feature_id({"properties": {"_id": ""}}, 3), 3)
        self.assertEqual(OSWSanitization._dataset_key_for_filename("city.edges.OSW.geojson"), "edges")
        self.assertIsNone(OSWSanitization._dataset_key_for_filename("city.buildings.geojson"))
        self.assertEqual(OSWSanitization._describe_non_finite(float("nan")), "NaN")
        self.assertEqual(OSWSanitization._sanitize_coordinates("raw", 0, "coordinates", [], SanitizationConfig()), "raw")

    def test_load_geojson_payload_raises_after_decode_failures(self):
        with patch(
            "builtins.open",
            side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "bad encoding"),
        ):
            with self.assertRaises(UnicodeDecodeError):
                OSWSanitization._load_geojson_payload("/fake/path.geojson")

    @staticmethod
    def _feature_collection(properties, coordinates, geometry_type="Point"):
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": properties,
                    "geometry": {
                        "type": geometry_type,
                        "coordinates": coordinates,
                    },
                }
            ],
        }

    @staticmethod
    def _line_coordinates(count):
        return [[index, index * 0.01] for index in range(count)]

    @staticmethod
    def _write_zip(zip_path, files):
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for filename, payload in files.items():
                if isinstance(payload, str):
                    zip_file.writestr(filename, payload)
                else:
                    zip_file.writestr(filename, json.dumps(payload, allow_nan=True))

    @staticmethod
    def _read_geojson_from_zip(zip_path, filename):
        with zipfile.ZipFile(zip_path, "r") as zip_file:
            with zip_file.open(filename) as geojson_file:
                return json.load(geojson_file)


if __name__ == "__main__":
    unittest.main()
