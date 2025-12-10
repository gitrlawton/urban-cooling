export interface HeatZone {
  id: number;
  geometry: {
    type: string;
    coordinates: number[][][];
  };
  heat_score: number;
  temp_celsius: number;
  priority: string;
  area_sqm: number;
}

export interface AnalyzeResponse {
  location: string;
  analysis_date: string;
  heat_zones: HeatZone[];
  metadata: {
    total_zones_analyzed: number;
    data_source: string;
  };
}

// Phase 2: Shade Analysis Types

export interface ShadeZone {
  id: number;
  geometry?: {
    type: string;
    coordinates: number[][][];
  };
  center?: {
    lat: number;
    lon: number;
  };
  heat_score: number;
  temp_celsius?: number;
  shade_coverage: number;
  shade_deficit: number;
  combined_score: number;
  priority: string;
  area_sqm?: number;
}

export interface HourlyCoverage {
  hour: number;
  coverage_percent: number;
  building_shade_percent?: number;
  tree_shade_percent?: number;
  is_night: boolean;
}

export interface ShadeMetadata {
  total_zones_analyzed: number;
  avg_shade_deficit: number;
  high_deficit_count: number;
  buildings_analyzed?: number;
  trees_analyzed?: number;
  simulation_date: string;
}

export interface ShadeAnalysisResponse {
  location: string;
  analysis_date: string;
  simulation_date: string;
  zones: ShadeZone[];
  hourly_coverage: HourlyCoverage[];
  metadata: ShadeMetadata;
}
