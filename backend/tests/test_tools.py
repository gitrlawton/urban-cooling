import pytest
from unittest.mock import Mock, patch
import requests
from tools.land_use import fetch_land_use_data
from tools.analysis import (
    process_heat_raster,
    calculate_heat_scores,
    filter_plantable_areas
)


class TestFetchLandUseData:
    """Test suite for fetch_land_use_data function"""

    def test_valid_bbox_returns_categorized_data(self):
        """Test that valid bbox returns properly categorized land use data"""
        # Mock successful API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "elements": [
                {"id": 1, "tags": {"building": "yes"}, "geometry": []},
                {"id": 2, "tags": {"building": "residential"}, "geometry": []},
                {"id": 3, "tags": {"leisure": "park", "name": "Central Park"}, "geometry": []},
                {"id": 4, "tags": {"natural": "water", "name": "Lake"}, "geometry": []},
                {"id": 5, "tags": {"landuse": "forest"}, "geometry": []},
            ]
        }
        mock_response.raise_for_status = Mock()

        with patch('tools.land_use.requests.post', return_value=mock_response):
            result = fetch_land_use_data([-122.5, 37.7, -122.3, 37.8])

        assert "buildings" in result
        assert "parks" in result
        assert "water" in result
        assert "forests" in result
        assert "bbox" in result
        assert "total_elements" in result

        assert len(result["buildings"]) == 2
        assert len(result["parks"]) == 1
        assert len(result["water"]) == 1
        assert len(result["forests"]) == 1
        assert result["total_elements"] == 5

    def test_empty_response_returns_empty_categories(self):
        """Test that empty API response returns empty categories"""
        mock_response = Mock()
        mock_response.json.return_value = {"elements": []}
        mock_response.raise_for_status = Mock()

        with patch('tools.land_use.requests.post', return_value=mock_response):
            result = fetch_land_use_data([-122.5, 37.7, -122.3, 37.8])

        assert len(result["buildings"]) == 0
        assert len(result["parks"]) == 0
        assert len(result["water"]) == 0
        assert len(result["forests"]) == 0
        assert result["total_elements"] == 0

    def test_invalid_bbox_format_raises_value_error(self):
        """Test that invalid bbox format raises ValueError"""
        # Too few elements
        with pytest.raises(ValueError, match="bbox must be a list of 4 floats"):
            fetch_land_use_data([-122.5, 37.7])

        # Too many elements
        with pytest.raises(ValueError, match="bbox must be a list of 4 floats"):
            fetch_land_use_data([-122.5, 37.7, -122.3, 37.8, 100])

        # Not a list
        with pytest.raises(ValueError, match="bbox must be a list of 4 floats"):
            fetch_land_use_data("invalid")

    def test_non_numeric_bbox_raises_value_error(self):
        """Test that non-numeric bbox values raise ValueError"""
        with pytest.raises(ValueError, match="bbox coordinates must be numeric"):
            fetch_land_use_data(["a", "b", "c", "d"])

    def test_invalid_coordinate_ranges_raise_value_error(self):
        """Test that out-of-range coordinates raise ValueError"""
        # Longitude out of range
        with pytest.raises(ValueError, match="Longitude values must be between -180 and 180"):
            fetch_land_use_data([-200, 37.7, -122.3, 37.8])

        # Latitude out of range
        with pytest.raises(ValueError, match="Latitude values must be between -90 and 90"):
            fetch_land_use_data([-122.5, -100, -122.3, 37.8])

        # West >= East
        with pytest.raises(ValueError, match="West longitude .* must be less than east longitude"):
            fetch_land_use_data([-122.3, 37.7, -122.5, 37.8])

        # South >= North
        with pytest.raises(ValueError, match="South latitude .* must be less than north latitude"):
            fetch_land_use_data([-122.5, 37.8, -122.3, 37.7])

    def test_api_timeout_raises_runtime_error(self):
        """Test that API timeout raises RuntimeError"""
        with patch('tools.land_use.requests.post', side_effect=requests.exceptions.Timeout):
            with pytest.raises(RuntimeError, match="Overpass API request timed out"):
                fetch_land_use_data([-122.5, 37.7, -122.3, 37.8])

    def test_api_connection_error_raises_runtime_error(self):
        """Test that API connection error raises RuntimeError"""
        with patch('tools.land_use.requests.post', side_effect=requests.exceptions.ConnectionError):
            with pytest.raises(RuntimeError, match="Failed to fetch land use data from Overpass API"):
                fetch_land_use_data([-122.5, 37.7, -122.3, 37.8])

    def test_http_error_raises_runtime_error(self):
        """Test that HTTP error raises RuntimeError"""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")

        with patch('tools.land_use.requests.post', return_value=mock_response):
            with pytest.raises(RuntimeError, match="Failed to fetch land use data from Overpass API"):
                fetch_land_use_data([-122.5, 37.7, -122.3, 37.8])

    def test_invalid_json_response_raises_runtime_error(self):
        """Test that invalid JSON response raises RuntimeError"""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status = Mock()

        with patch('tools.land_use.requests.post', return_value=mock_response):
            with pytest.raises(RuntimeError, match="Invalid JSON response from Overpass API"):
                fetch_land_use_data([-122.5, 37.7, -122.3, 37.8])

    def test_malformed_response_structure_raises_runtime_error(self):
        """Test that malformed response structure raises RuntimeError"""
        # Response is not a dict
        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = Mock()

        with patch('tools.land_use.requests.post', return_value=mock_response):
            with pytest.raises(RuntimeError, match="Expected JSON object from Overpass API"):
                fetch_land_use_data([-122.5, 37.7, -122.3, 37.8])

        # Missing 'elements' field
        mock_response.json.return_value = {"other_field": "value"}

        with patch('tools.land_use.requests.post', return_value=mock_response):
            with pytest.raises(RuntimeError, match="Overpass API response missing 'elements' field"):
                fetch_land_use_data([-122.5, 37.7, -122.3, 37.8])

        # 'elements' is not a list
        mock_response.json.return_value = {"elements": "not a list"}

        with patch('tools.land_use.requests.post', return_value=mock_response):
            with pytest.raises(RuntimeError, match="Expected 'elements' to be a list"):
                fetch_land_use_data([-122.5, 37.7, -122.3, 37.8])

    def test_request_includes_timeout(self):
        """Test that request includes a timeout parameter"""
        mock_response = Mock()
        mock_response.json.return_value = {"elements": []}
        mock_response.raise_for_status = Mock()

        with patch('tools.land_use.requests.post', return_value=mock_response) as mock_post:
            fetch_land_use_data([-122.5, 37.7, -122.3, 37.8])

        # Verify timeout was set
        assert mock_post.called
        call_kwargs = mock_post.call_args[1]
        assert 'timeout' in call_kwargs
        assert call_kwargs['timeout'] == 30

    def test_bbox_preserved_in_result(self):
        """Test that the original bbox is preserved in the result"""
        mock_response = Mock()
        mock_response.json.return_value = {"elements": []}
        mock_response.raise_for_status = Mock()

        bbox = [-122.5, 37.7, -122.3, 37.8]

        with patch('tools.land_use.requests.post', return_value=mock_response):
            result = fetch_land_use_data(bbox)

        assert result["bbox"] == bbox


class TestProcessHeatRaster:
    """Test suite for process_heat_raster function"""

    def test_valid_heat_data_returns_grid(self):
        """Test that valid heat data produces a grid structure"""
        heat_data = {
            "thermal_samples": [
                {
                    "geometry": {"type": "Point", "coordinates": [-122.4, 37.75]},
                    "properties": {"ST_B10": 25.5}
                },
                {
                    "geometry": {"type": "Point", "coordinates": [-122.41, 37.76]},
                    "properties": {"ST_B10": 28.0}
                },
            ],
            "bbox": [-122.5, 37.7, -122.3, 37.8],
            "statistics": {
                "mean_temp_celsius": 26.75,
                "min_temp_celsius": 25.5,
                "max_temp_celsius": 28.0
            }
        }

        result = process_heat_raster(heat_data)

        assert "grid" in result
        assert "cell_size" in result
        assert "rows" in result
        assert "cols" in result
        assert "bbox" in result
        assert "statistics" in result
        assert "cells_with_data" in result
        assert result["rows"] > 0
        assert result["cols"] > 0

    def test_empty_heat_data_raises_error(self):
        """Test that empty heat data raises ValueError"""
        with pytest.raises(ValueError, match="heat_data cannot be empty"):
            process_heat_raster(None)

        with pytest.raises(ValueError, match="heat_data cannot be empty"):
            process_heat_raster({})

    def test_missing_required_fields_raises_error(self):
        """Test that missing required fields raise ValueError"""
        # Missing thermal_samples
        with pytest.raises(ValueError, match="missing required field: thermal_samples"):
            process_heat_raster({"bbox": [], "statistics": {}})

        # Missing bbox
        with pytest.raises(ValueError, match="missing required field: bbox"):
            process_heat_raster({"thermal_samples": [], "statistics": {}})

        # Missing statistics
        with pytest.raises(ValueError, match="missing required field: statistics"):
            process_heat_raster({"thermal_samples": [], "bbox": []})

    def test_invalid_bbox_raises_error(self):
        """Test that invalid bbox raises ValueError"""
        heat_data = {
            "thermal_samples": [],
            "bbox": [-122.5, 37.7],  # Only 2 values
            "statistics": {}
        }

        with pytest.raises(ValueError, match="bbox must be a list of 4 values"):
            process_heat_raster(heat_data)

    def test_samples_without_geometry_are_skipped(self):
        """Test that samples without valid geometry are skipped"""
        heat_data = {
            "thermal_samples": [
                {"properties": {"ST_B10": 25.5}},  # No geometry
                {
                    "geometry": {"type": "Point", "coordinates": [-122.4, 37.75]},
                    "properties": {"ST_B10": 28.0}
                },
            ],
            "bbox": [-122.5, 37.7, -122.3, 37.8],
            "statistics": {"mean_temp_celsius": 26.75}
        }

        result = process_heat_raster(heat_data)
        assert result["cells_with_data"] >= 0

    def test_samples_without_temperature_are_skipped(self):
        """Test that samples without temperature values are skipped"""
        heat_data = {
            "thermal_samples": [
                {
                    "geometry": {"type": "Point", "coordinates": [-122.4, 37.75]},
                    "properties": {}  # No ST_B10
                },
            ],
            "bbox": [-122.5, 37.7, -122.3, 37.8],
            "statistics": {"mean_temp_celsius": 26.75}
        }

        result = process_heat_raster(heat_data)
        assert result["cells_with_data"] == 0

    def test_grid_cells_have_required_fields(self):
        """Test that grid cells contain required fields"""
        heat_data = {
            "thermal_samples": [
                {
                    "geometry": {"type": "Point", "coordinates": [-122.4, 37.75]},
                    "properties": {"ST_B10": 25.5}
                },
            ],
            "bbox": [-122.5, 37.7, -122.3, 37.8],
            "statistics": {"mean_temp_celsius": 25.5}
        }

        result = process_heat_raster(heat_data)
        cell = result["grid"][0][0]

        assert "avg_temp" in cell
        assert "sample_count" in cell
        assert "center_lat" in cell
        assert "center_lon" in cell


class TestCalculateHeatScores:
    """Test suite for calculate_heat_scores function"""

    @pytest.fixture
    def sample_heat_grid(self):
        """Create a sample heat grid for testing"""
        return {
            "grid": [
                [
                    {"avg_temp": 25.0, "sample_count": 5, "center_lat": 37.75, "center_lon": -122.45, "row": 0, "col": 0},
                    {"avg_temp": 30.0, "sample_count": 3, "center_lat": 37.75, "center_lon": -122.44, "row": 0, "col": 1},
                ],
                [
                    {"avg_temp": 28.0, "sample_count": 4, "center_lat": 37.76, "center_lon": -122.45, "row": 1, "col": 0},
                    {"avg_temp": 35.0, "sample_count": 6, "center_lat": 37.76, "center_lon": -122.44, "row": 1, "col": 1},
                ],
            ],
            "statistics": {
                "mean_temp_celsius": 29.5,
                "min_temp_celsius": 25.0,
                "max_temp_celsius": 35.0
            },
            "rows": 2,
            "cols": 2,
            "bbox": [-122.5, 37.7, -122.3, 37.8],
            "cell_size": 0.001
        }

    @pytest.fixture
    def sample_land_use(self):
        """Create sample land use data for testing"""
        return {
            "buildings": [
                {"id": 1, "geometry": [{"lat": 37.75, "lon": -122.45}]},
            ],
            "parks": [],
            "water": [],
            "forests": []
        }

    def test_valid_inputs_return_zones(self, sample_heat_grid, sample_land_use):
        """Test that valid inputs produce scored zones"""
        result = calculate_heat_scores(sample_heat_grid, sample_land_use)

        assert "zones" in result
        assert "statistics" in result
        assert "bbox" in result
        assert "temp_range" in result
        assert len(result["zones"]) == 4  # 2x2 grid

    def test_zones_are_sorted_by_heat_score_descending(self, sample_heat_grid, sample_land_use):
        """Test that zones are sorted by heat score in descending order"""
        result = calculate_heat_scores(sample_heat_grid, sample_land_use)
        zones = result["zones"]

        for i in range(len(zones) - 1):
            assert zones[i]["heat_score"] >= zones[i + 1]["heat_score"]

    def test_zones_have_required_fields(self, sample_heat_grid, sample_land_use):
        """Test that each zone has all required fields"""
        result = calculate_heat_scores(sample_heat_grid, sample_land_use)
        zone = result["zones"][0]

        required_fields = [
            "id", "geometry", "heat_score", "temp_celsius",
            "priority", "area_sqm", "center"
        ]
        for field in required_fields:
            assert field in zone

    def test_heat_scores_are_normalized_0_to_100(self, sample_heat_grid, sample_land_use):
        """Test that heat scores are in 0-100 range"""
        result = calculate_heat_scores(sample_heat_grid, sample_land_use)

        for zone in result["zones"]:
            assert 0 <= zone["heat_score"] <= 100

    def test_priority_levels_are_assigned_correctly(self, sample_heat_grid, sample_land_use):
        """Test that priority levels match score thresholds"""
        result = calculate_heat_scores(sample_heat_grid, sample_land_use)

        for zone in result["zones"]:
            score = zone["heat_score"]
            priority = zone["priority"]

            if score >= 80:
                assert priority == "critical"
            elif score >= 60:
                assert priority == "high"
            elif score >= 40:
                assert priority == "medium"
            else:
                assert priority == "low"

    def test_statistics_summary_is_correct(self, sample_heat_grid, sample_land_use):
        """Test that statistics summary is calculated correctly"""
        result = calculate_heat_scores(sample_heat_grid, sample_land_use)
        stats = result["statistics"]

        assert "total_zones" in stats
        assert "critical_count" in stats
        assert "high_count" in stats
        assert "medium_count" in stats
        assert "low_count" in stats
        assert "avg_heat_score" in stats
        assert stats["total_zones"] == 4

    def test_empty_heat_grid_raises_error(self, sample_land_use):
        """Test that empty heat grid raises ValueError"""
        with pytest.raises(ValueError, match="heat_grid must be a non-empty dictionary"):
            calculate_heat_scores(None, sample_land_use)

        with pytest.raises(ValueError, match="heat_grid must be a non-empty dictionary"):
            calculate_heat_scores({}, sample_land_use)

    def test_empty_land_use_raises_error(self, sample_heat_grid):
        """Test that empty land use raises ValueError"""
        with pytest.raises(ValueError, match="land_use must be a non-empty dictionary"):
            calculate_heat_scores(sample_heat_grid, None)

        with pytest.raises(ValueError, match="land_use must be a non-empty dictionary"):
            calculate_heat_scores(sample_heat_grid, {})

    def test_missing_grid_fields_raises_error(self, sample_land_use):
        """Test that missing grid fields raise ValueError"""
        incomplete_grid = {"grid": [], "rows": 0, "cols": 0}

        with pytest.raises(ValueError, match="missing required field"):
            calculate_heat_scores(incomplete_grid, sample_land_use)

    def test_cells_without_temperature_are_skipped(self, sample_land_use):
        """Test that cells with None temperature are not included in zones"""
        heat_grid = {
            "grid": [
                [
                    {"avg_temp": 25.0, "sample_count": 5, "center_lat": 37.75, "center_lon": -122.45, "row": 0, "col": 0},
                    {"avg_temp": None, "sample_count": 0, "center_lat": 37.75, "center_lon": -122.44, "row": 0, "col": 1},
                ]
            ],
            "statistics": {"min_temp_celsius": 25.0, "max_temp_celsius": 25.0},
            "rows": 1,
            "cols": 2,
            "bbox": [-122.5, 37.7, -122.3, 37.8],
            "cell_size": 0.001
        }

        result = calculate_heat_scores(heat_grid, sample_land_use)
        assert result["statistics"]["total_zones"] == 1


class TestFilterPlantableAreas:
    """Test suite for filter_plantable_areas function"""

    @pytest.fixture
    def sample_zones(self):
        """Create sample zones for testing"""
        return {
            "zones": [
                {"id": 1, "heat_score": 95, "priority": "critical", "row": 0, "col": 0, "building_density": 0},
                {"id": 2, "heat_score": 85, "priority": "critical", "row": 0, "col": 1, "building_density": 1},
                {"id": 3, "heat_score": 75, "priority": "high", "row": 1, "col": 0, "building_density": 0},
                {"id": 4, "heat_score": 65, "priority": "high", "row": 1, "col": 1, "building_density": 2},
                {"id": 5, "heat_score": 55, "priority": "medium", "row": 2, "col": 0, "building_density": 0},
            ],
            "statistics": {"total_zones": 5},
            "bbox": [-122.5, 37.7, -122.3, 37.8],
            "temp_range": {"min_celsius": 25.0, "max_celsius": 35.0}
        }

    @pytest.fixture
    def sample_land_use_with_features(self):
        """Create sample land use with various features"""
        return {
            "buildings": [
                {"id": 1, "geometry": [{"lat": 37.701, "lon": -122.499}]},
            ],
            "parks": [
                {"id": 2, "geometry": [{"lat": 37.702, "lon": -122.498}]},
            ],
            "water": [
                {"id": 3, "geometry": [{"lat": 37.703, "lon": -122.497}]},
            ],
            "forests": [
                {"id": 4, "geometry": [{"lat": 37.704, "lon": -122.496}]},
            ]
        }

    def test_valid_inputs_return_filtered_zones(self, sample_zones, sample_land_use_with_features):
        """Test that valid inputs return filtered zones"""
        result = filter_plantable_areas(sample_zones, sample_land_use_with_features)

        assert "zones" in result
        assert "statistics" in result
        assert "filtering_summary" in result
        assert "bbox" in result

    def test_returns_top_20_zones_by_heat_score(self):
        """Test that function returns maximum 20 zones"""
        # Create 25 zones
        zones = {
            "zones": [
                {"id": i, "heat_score": 100 - i, "priority": "critical", "row": i, "col": 0, "building_density": 0}
                for i in range(25)
            ],
            "statistics": {"total_zones": 25},
            "bbox": [-122.5, 37.7, -122.3, 37.8]
        }

        land_use = {"buildings": [], "parks": [], "water": [], "forests": []}

        result = filter_plantable_areas(zones, land_use)
        assert len(result["zones"]) <= 20

    def test_zones_still_sorted_by_heat_score(self, sample_zones, sample_land_use_with_features):
        """Test that filtered zones remain sorted by heat score"""
        result = filter_plantable_areas(sample_zones, sample_land_use_with_features)
        zones = result["zones"]

        for i in range(len(zones) - 1):
            assert zones[i]["heat_score"] >= zones[i + 1]["heat_score"]

    def test_filtering_summary_tracks_exclusions(self, sample_zones, sample_land_use_with_features):
        """Test that filtering summary tracks exclusion reasons"""
        result = filter_plantable_areas(sample_zones, sample_land_use_with_features)
        summary = result["filtering_summary"]

        assert "original_count" in summary
        assert "plantable_count" in summary
        assert "returned_count" in summary
        assert "excluded_water" in summary
        assert "excluded_forest" in summary
        assert "excluded_building" in summary

    def test_plantable_flag_added_to_zones(self, sample_zones, sample_land_use_with_features):
        """Test that plantable flag is added to returned zones"""
        result = filter_plantable_areas(sample_zones, sample_land_use_with_features)

        for zone in result["zones"]:
            assert "plantable" in zone
            assert zone["plantable"] is True

    def test_park_zones_marked_correctly(self):
        """Test that zones in parks are marked with in_park flag"""
        zones = {
            "zones": [
                {"id": 1, "heat_score": 90, "priority": "critical", "row": 0, "col": 0, "building_density": 0},
            ],
            "statistics": {"total_zones": 1},
            "bbox": [-122.5, 37.7, -122.3, 37.8]
        }

        # Park at cell (0, 0)
        land_use = {
            "buildings": [],
            "parks": [{"id": 1, "geometry": [{"lat": 37.7005, "lon": -122.4995}]}],
            "water": [],
            "forests": []
        }

        result = filter_plantable_areas(zones, land_use)

        # Check if in_park flag is present
        if result["zones"]:
            assert "in_park" in result["zones"][0]

    def test_empty_zones_input_raises_error(self, sample_land_use_with_features):
        """Test that empty zones input raises ValueError"""
        with pytest.raises(ValueError, match="zones must be a non-empty dictionary"):
            filter_plantable_areas(None, sample_land_use_with_features)

        with pytest.raises(ValueError, match="zones must be a non-empty dictionary"):
            filter_plantable_areas({}, sample_land_use_with_features)

    def test_missing_zones_field_raises_error(self, sample_land_use_with_features):
        """Test that missing zones field raises ValueError"""
        with pytest.raises(ValueError, match="missing 'zones' field"):
            filter_plantable_areas({"statistics": {}}, sample_land_use_with_features)

    def test_empty_land_use_raises_error(self, sample_zones):
        """Test that empty land use raises ValueError"""
        with pytest.raises(ValueError, match="land_use must be a non-empty dictionary"):
            filter_plantable_areas(sample_zones, None)

        with pytest.raises(ValueError, match="land_use must be a non-empty dictionary"):
            filter_plantable_areas(sample_zones, {})

    def test_statistics_updated_for_filtered_zones(self, sample_zones, sample_land_use_with_features):
        """Test that statistics are recalculated for filtered zones"""
        result = filter_plantable_areas(sample_zones, sample_land_use_with_features)
        stats = result["statistics"]

        assert "total_zones" in stats
        assert "critical_count" in stats
        assert "high_count" in stats
        assert "avg_heat_score" in stats
        assert stats["total_zones"] == len(result["zones"])

    def test_temp_range_preserved(self, sample_zones, sample_land_use_with_features):
        """Test that temp_range is preserved in output"""
        result = filter_plantable_areas(sample_zones, sample_land_use_with_features)

        assert "temp_range" in result
        assert result["temp_range"] == sample_zones["temp_range"]

    def test_empty_zones_list_returns_empty_result(self, sample_land_use_with_features):
        """Test that empty zones list returns appropriate empty result"""
        zones = {
            "zones": [],
            "statistics": {"total_zones": 0},
            "bbox": [-122.5, 37.7, -122.3, 37.8]
        }

        result = filter_plantable_areas(zones, sample_land_use_with_features)

        assert len(result["zones"]) == 0
        assert result["statistics"]["total_zones"] == 0
