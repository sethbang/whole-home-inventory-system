/**
 * Shared types for the Settings page and its tab subcomponents.
 */

export type TabId = 'provider' | 'models' | 'budget' | 'test';

export interface FormValues {
  base_url: string;
  api_key: string;
  model: string;
  vision_model: string;
  pricing_model: string;
  timeout_seconds: number;
  response_healing: boolean;
  vision_enabled: boolean;
  pricing_enabled: boolean;
  vision_daily_cap_usd: number;
  pricing_daily_cap_usd: number;
}
