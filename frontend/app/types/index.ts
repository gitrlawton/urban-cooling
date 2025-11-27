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
