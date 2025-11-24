import pytest
from unittest.mock import Mock, patch
import requests
from tools.land_use import fetch_land_use_data


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
