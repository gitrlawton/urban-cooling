"""
Tests for the Urban Cooling Analyst Agent

These tests verify the agent can be instantiated and tools work correctly.
Note: Full end-to-end tests require API keys and external services.
"""

import pytest
from unittest.mock import patch, Mock


class TestUrbanCoolingAnalystAgent:
    """Test suite for Urban Cooling Analyst Agent"""

    def test_agent_tools_are_callable(self):
        """Test that all agent tool functions are defined and callable"""
        from agents.urban_cooling_analyst import (
            geocode,
            get_heat_data,
            get_land_use,
            process_thermal_data,
            score_heat_zones,
            filter_plantable_zones
        )

        # Verify all tools are callable
        assert callable(geocode)
        assert callable(get_heat_data)
        assert callable(get_land_use)
        assert callable(process_thermal_data)
        assert callable(score_heat_zones)
        assert callable(filter_plantable_zones)

    def test_geocode_tool_calls_underlying_function(self):
        """Test that geocode tool delegates to geocode_location"""
        from agents.urban_cooling_analyst import geocode

        mock_result = {
            "location_name": "San Francisco, CA, USA",
            "bbox": [-122.5, 37.7, -122.3, 37.8],
            "center": {"lat": 37.75, "lon": -122.4}
        }

        with patch('agents.urban_cooling_analyst.geocode_location', return_value=mock_result) as mock_func:
            result = geocode("San Francisco, CA")

            mock_func.assert_called_once_with("San Francisco, CA")
            assert result == mock_result

    def test_get_heat_data_tool_constructs_bbox(self):
        """Test that get_heat_data constructs bbox from individual coordinates"""
        from agents.urban_cooling_analyst import get_heat_data

        mock_result = {
            "thermal_samples": [],
            "bbox": [-122.5, 37.7, -122.3, 37.8],
            "statistics": {}
        }

        with patch('agents.urban_cooling_analyst.fetch_heat_data', return_value=mock_result) as mock_func:
            result = get_heat_data(-122.5, 37.7, -122.3, 37.8)

            mock_func.assert_called_once_with([-122.5, 37.7, -122.3, 37.8], "2024-06-01,2024-08-31")
            assert result == mock_result

    def test_get_heat_data_tool_accepts_custom_date_range(self):
        """Test that get_heat_data accepts custom date range"""
        from agents.urban_cooling_analyst import get_heat_data

        mock_result = {"thermal_samples": [], "bbox": [], "statistics": {}}

        with patch('agents.urban_cooling_analyst.fetch_heat_data', return_value=mock_result) as mock_func:
            get_heat_data(-122.5, 37.7, -122.3, 37.8, "2023-07-01,2023-07-31")

            mock_func.assert_called_once_with(
                [-122.5, 37.7, -122.3, 37.8],
                "2023-07-01,2023-07-31"
            )

    def test_get_land_use_tool_constructs_bbox(self):
        """Test that get_land_use constructs bbox from individual coordinates"""
        from agents.urban_cooling_analyst import get_land_use

        mock_result = {
            "buildings": [],
            "parks": [],
            "water": [],
            "forests": [],
            "bbox": [-122.5, 37.7, -122.3, 37.8]
        }

        with patch('agents.urban_cooling_analyst.fetch_land_use_data', return_value=mock_result) as mock_func:
            result = get_land_use(-122.5, 37.7, -122.3, 37.8)

            mock_func.assert_called_once_with([-122.5, 37.7, -122.3, 37.8])
            assert result == mock_result

    def test_process_thermal_data_handles_dict_input(self):
        """Test that process_thermal_data accepts dict input"""
        from agents.urban_cooling_analyst import process_thermal_data

        heat_data = {
            "thermal_samples": [],
            "bbox": [-122.5, 37.7, -122.3, 37.8],
            "statistics": {"mean_temp_celsius": 25.0}
        }

        mock_result = {"grid": [], "rows": 0, "cols": 0}

        with patch('agents.urban_cooling_analyst.process_heat_raster', return_value=mock_result) as mock_func:
            result = process_thermal_data(heat_data)

            mock_func.assert_called_once_with(heat_data)
            assert result == mock_result

    def test_process_thermal_data_handles_json_string_input(self):
        """Test that process_thermal_data accepts JSON string input"""
        import json
        from agents.urban_cooling_analyst import process_thermal_data

        heat_data = {
            "thermal_samples": [],
            "bbox": [-122.5, 37.7, -122.3, 37.8],
            "statistics": {"mean_temp_celsius": 25.0}
        }

        mock_result = {"grid": [], "rows": 0, "cols": 0}

        with patch('agents.urban_cooling_analyst.process_heat_raster', return_value=mock_result) as mock_func:
            result = process_thermal_data(json.dumps(heat_data))

            mock_func.assert_called_once_with(heat_data)
            assert result == mock_result

    def test_score_heat_zones_handles_dict_inputs(self):
        """Test that score_heat_zones accepts dict inputs"""
        from agents.urban_cooling_analyst import score_heat_zones

        heat_grid = {"grid": [], "rows": 1, "cols": 1, "statistics": {}, "bbox": [], "cell_size": 0.001}
        land_use = {"buildings": [], "parks": [], "water": [], "forests": []}

        mock_result = {"zones": [], "statistics": {}}

        with patch('agents.urban_cooling_analyst.calculate_heat_scores', return_value=mock_result) as mock_func:
            result = score_heat_zones(heat_grid, land_use)

            mock_func.assert_called_once_with(heat_grid, land_use)
            assert result == mock_result

    def test_filter_plantable_zones_handles_dict_inputs(self):
        """Test that filter_plantable_zones accepts dict inputs"""
        from agents.urban_cooling_analyst import filter_plantable_zones

        zones = {"zones": [], "statistics": {}, "bbox": []}
        land_use = {"buildings": [], "parks": [], "water": [], "forests": []}

        mock_result = {"zones": [], "statistics": {}, "filtering_summary": {}}

        with patch('agents.urban_cooling_analyst.filter_plantable_areas', return_value=mock_result) as mock_func:
            result = filter_plantable_zones(zones, land_use)

            mock_func.assert_called_once_with(zones, land_use)
            assert result == mock_result

    def test_agent_has_correct_name(self):
        """Test that the agent has the correct name"""
        # Import with mocked ADK to avoid requiring API keys
        with patch('google.adk.agents.Agent') as MockAgent:
            MockAgent.return_value = Mock()

            # Re-import to trigger agent creation with mock
            import importlib
            import agents.urban_cooling_analyst as agent_module
            importlib.reload(agent_module)

            # Check the agent was created with correct name
            call_kwargs = MockAgent.call_args[1]
            assert call_kwargs['name'] == 'urban_cooling_analyst'
            assert 'gemini' in call_kwargs['model'].lower()
            assert len(call_kwargs['tools']) == 6

    def test_agent_tools_have_docstrings(self):
        """Test that all tool functions have proper docstrings"""
        from agents.urban_cooling_analyst import (
            geocode,
            get_heat_data,
            get_land_use,
            process_thermal_data,
            score_heat_zones,
            filter_plantable_zones
        )

        tools = [
            geocode,
            get_heat_data,
            get_land_use,
            process_thermal_data,
            score_heat_zones,
            filter_plantable_zones
        ]

        for tool in tools:
            assert tool.__doc__ is not None, f"{tool.__name__} missing docstring"
            assert len(tool.__doc__) > 20, f"{tool.__name__} docstring too short"


class TestAgentToolIntegration:
    """Integration tests for agent tools working together"""

    def test_full_pipeline_with_mocked_external_calls(self):
        """Test the full analysis pipeline with mocked external API calls"""
        from agents.urban_cooling_analyst import (
            geocode,
            get_heat_data,
            get_land_use,
            process_thermal_data,
            score_heat_zones,
            filter_plantable_zones
        )

        # Mock geocode response
        geocode_result = {
            "location_name": "Test City, CA, USA",
            "bbox": [-122.5, 37.7, -122.3, 37.8],
            "center": {"lat": 37.75, "lon": -122.4}
        }

        # Mock heat data response
        heat_data_result = {
            "thermal_samples": [
                {
                    "geometry": {"type": "Point", "coordinates": [-122.4, 37.75]},
                    "properties": {"ST_B10": 30.0}
                }
            ],
            "bbox": [-122.5, 37.7, -122.3, 37.8],
            "statistics": {
                "mean_temp_celsius": 30.0,
                "min_temp_celsius": 25.0,
                "max_temp_celsius": 35.0
            }
        }

        # Mock land use response
        land_use_result = {
            "buildings": [],
            "parks": [],
            "water": [],
            "forests": [],
            "bbox": [-122.5, 37.7, -122.3, 37.8],
            "total_elements": 0
        }

        with patch('agents.urban_cooling_analyst.geocode_location', return_value=geocode_result):
            with patch('agents.urban_cooling_analyst.fetch_heat_data', return_value=heat_data_result):
                with patch('agents.urban_cooling_analyst.fetch_land_use_data', return_value=land_use_result):
                    # Step 1: Geocode
                    geo = geocode("Test City, CA")
                    assert "bbox" in geo

                    # Step 2: Get heat data
                    bbox = geo["bbox"]
                    heat = get_heat_data(bbox[0], bbox[1], bbox[2], bbox[3])
                    assert "thermal_samples" in heat

                    # Step 3: Get land use
                    land = get_land_use(bbox[0], bbox[1], bbox[2], bbox[3])
                    assert "buildings" in land

                    # Step 4: Process thermal data (uses real function)
                    grid = process_thermal_data(heat)
                    assert "grid" in grid

                    # Step 5: Score zones (uses real function)
                    scored = score_heat_zones(grid, land)
                    assert "zones" in scored

                    # Step 6: Filter plantable zones (uses real function)
                    filtered = filter_plantable_zones(scored, land)
                    assert "zones" in filtered
                    assert "filtering_summary" in filtered
