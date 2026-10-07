/**
 * Budget tab — daily USD cost caps for vision and pricing, today's
 * spend readouts, and the two feature-enable toggles.
 */

import { useForm } from 'react-hook-form';

import type { LLMConfigRead } from '../../api/types';
import { SourceTag } from './badges';
import type { FormValues } from './types';

type RegisterFn = ReturnType<typeof useForm<FormValues>>['register'];

interface BudgetTabProps {
  register: RegisterFn;
  cfg: LLMConfigRead;
  sources: Record<string, string>;
}

export default function BudgetTab({ register, cfg, sources }: BudgetTabProps) {
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-muted">
            Vision daily cap (USD){' '}
            <SourceTag source={sources.vision_daily_cap_usd} />
          </label>
          <input
            type="number"
            step="0.5"
            min={0}
            {...register('vision_daily_cap_usd', { valueAsNumber: true })}
            className="mt-1 block w-full rounded-md border-line-strong shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
          />
          <p className="mt-1 text-xs text-muted">
            Today's spend:{' '}
            <strong>${(cfg.today_vision_cost_usd ?? 0).toFixed(4)}</strong>
          </p>
        </div>
        <div>
          <label className="block text-sm font-medium text-muted">
            Pricing daily cap (USD){' '}
            <SourceTag source={sources.pricing_daily_cap_usd} />
          </label>
          <input
            type="number"
            step="0.5"
            min={0}
            {...register('pricing_daily_cap_usd', { valueAsNumber: true })}
            className="mt-1 block w-full rounded-md border-line-strong shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
          />
          <p className="mt-1 text-xs text-muted">
            Today's spend:{' '}
            <strong>${(cfg.today_pricing_cost_usd ?? 0).toFixed(4)}</strong>
          </p>
        </div>
      </div>

      <div className="space-y-3 border-t pt-4">
        <label className="inline-flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            {...register('vision_enabled')}
            className="h-4 w-4 rounded border-line-strong text-primary focus:ring-primary"
          />
          Vision auto-fill enabled
          <SourceTag source={sources.vision_enabled} />
        </label>
        <br />
        <label className="inline-flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            {...register('pricing_enabled')}
            className="h-4 w-4 rounded border-line-strong text-primary focus:ring-primary"
          />
          Pricing estimates enabled
          <SourceTag source={sources.pricing_enabled} />
        </label>
      </div>
    </div>
  );
}
