export interface PropertyLookupResult {
  id: string;
  parcel_id: string;
  address_full: string;
  zip_code: string | null;
  property_category: PropertyCategory;
  current_assessed_total: number | null;
  similarity: number;
}

export type PropertyCategory =
  | 'rowhouse'
  | 'twin_semi'
  | 'single_family'
  | 'multi_family'
  | 'condo'
  | 'mixed_use'
  | 'commercial'
  | 'vacant'
  | 'other';

export interface SaleRead {
  sale_date: string;
  sale_price: number;
  deed_type: string | null;
  grantor: string | null;
  grantee: string | null;
  is_arms_length: boolean | null;
}

export interface PropertyDetail {
  id: string;
  county_id: string;
  parcel_id: string;
  address_full: string;
  address_normalized: string;
  street_number: string | null;
  street_direction: string | null;
  street_name: string | null;
  street_suffix: string | null;
  unit: string | null;
  city: string | null;
  state: string;
  zip_code: string | null;
  property_category: PropertyCategory;
  source_property_type: string | null;
  year_built: number | null;
  square_feet_living: number | null;
  square_feet_lot: number | null;
  number_of_bedrooms: number | null;
  number_of_bathrooms: number | null;
  number_of_stories: number | null;
  current_assessed_total: number | null;
  current_assessed_land: number | null;
  current_assessed_building: number | null;
  current_assessment_year: number | null;
  last_sale_date: string | null;
  last_sale_price: number | null;
  source_id: string;
  created_at: string;
  updated_at: string;
  sales: SaleRead[];
}

export type CompGeographicScope = 'same_block' | 'same_census_tract' | 'same_ward';
export type ValuationConfidence = 'high' | 'medium' | 'low' | 'insufficient_data';
export type CompSizeMatch = 'tight' | 'loose';

export interface CompUsed {
  property_id: string;
  address_full: string;
  parcel_id: string;
  sale_date: string;
  sale_price: number;
  sale_price_adjusted: number;
  living_area: number | null;
  price_per_sqft: number | null;
  similarity_score: number;
  geographic_scope: CompGeographicScope;
  size_match: CompSizeMatch;
  months_ago: number;
}

export interface Valuation {
  subject_property_id: string;
  point_estimate: number | null;
  low_estimate: number | null;
  high_estimate: number | null;
  confidence: ValuationConfidence;
  comp_count: number;
  comps: CompUsed[];
  notes: string[];
  time_adjustment_rate_annual: number;
  calculated_at: string | null;
}

export type UniformitySignal =
  | 'strong_case'
  | 'moderate_case'
  | 'weak_case'
  | 'no_case'
  | 'insufficient_data';

export interface NeighborhoodAsr {
  property_id: string;
  address_full: string;
  parcel_id: string;
  sale_date: string;
  sale_price: number;
  assessment: number;
  asr: number;
}

export interface BlockUniformity {
  block_id: string;
  median_asr: number;
  sample_size: number;
  asr_p25: number;
  asr_p75: number;
  samples: NeighborhoodAsr[];
}

export interface Uniformity {
  subject_property_id: string;
  subject_asr: number | null;
  subject_asr_source: string;
  neighborhood_median_asr: number | null;
  neighborhood_sample_size: number;
  block_result: BlockUniformity | null;
  deviation_from_neighborhood: number | null;
  deviation_from_block: number | null;
  signal: UniformitySignal;
  notes: string[];
  calculated_at: string | null;
}

export type AppealRecommendation =
  | 'appeal_strongly'
  | 'appeal'
  | 'marginal'
  | 'do_not_appeal'
  | 'insufficient_data';

export type AppealArgument = 'market_value' | 'uniformity' | 'both' | 'none';
export type CounterAppealRisk = 'low' | 'medium' | 'high' | 'unknown';
export type RecommendationConfidence = 'high' | 'medium' | 'low';

export interface Recommendation {
  subject_property_id: string;
  recommendation: AppealRecommendation;
  primary_argument: AppealArgument;
  confidence: RecommendationConfidence;
  current_assessment: number;
  market_value_estimate: number | null;
  appeal_target_assessment: number | null;
  annual_tax_savings: number | null;
  three_year_savings: number | null;
  counter_appeal_risk: CounterAppealRisk;
  reasoning: string[];
  calculated_at: string | null;
}

export interface County {
  id: string;
  name: string;
  state: string;
  slug: string;
}