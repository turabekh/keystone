import { api } from 'src/boot/axios';
import type {
  PropertyDetail,
  PropertyLookupResult,
  Recommendation,
  Uniformity,
  Valuation,
} from 'src/types/api';

export interface LookupParams {
  q: string;
  state: string;
  county_slug: string;
  limit?: number;
}

export const propertiesService = {
  async lookup(params: LookupParams): Promise<PropertyLookupResult[]> {
    const response = await api.get<PropertyLookupResult[]>('/api/v1/properties/lookup', {
      params: { limit: 10, ...params },
    });
    return response.data;
  },

  async getDetail(id: string): Promise<PropertyDetail> {
    const response = await api.get<PropertyDetail>(`/api/v1/properties/${id}`);
    return response.data;
  },

  async getValuation(id: string): Promise<Valuation> {
    const response = await api.get<Valuation>(`/api/v1/properties/${id}/valuation`);
    return response.data;
  },

  async getUniformity(id: string): Promise<Uniformity> {
    const response = await api.get<Uniformity>(`/api/v1/properties/${id}/uniformity`);
    return response.data;
  },

  async getRecommendation(id: string): Promise<Recommendation> {
    const response = await api.get<Recommendation>(`/api/v1/properties/${id}/recommendation`);
    return response.data;
  },
};