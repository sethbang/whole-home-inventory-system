/**
 * Models tab — pick which provider model fills each role (default /
 * vision / pricing) and browse the provider's model catalogue with
 * capability filters.
 */

import { useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';

import type { LLMModelEntry } from '../../api/types';
import { CapabilityBadge, SourceTag } from './badges';
import type { FormValues } from './types';

type RegisterFn = ReturnType<typeof useForm<FormValues>>['register'];
type WatchFn = ReturnType<typeof useForm<FormValues>>['watch'];
type SetValueFn = ReturnType<typeof useForm<FormValues>>['setValue'];

type ModelFilter = 'all' | 'vision' | 'strict-json';

interface ModelsTabProps {
  register: RegisterFn;
  watch: WatchFn;
  setValue: SetValueFn;
  models: LLMModelEntry[];
  isLoading: boolean;
  error: string | null;
  onRefresh: () => void;
  sources: Record<string, string>;
}

function ModelSelectField({
  label,
  fieldName,
  register,
  source,
}: {
  label: string;
  fieldName: 'model' | 'vision_model' | 'pricing_model';
  register: RegisterFn;
  source: string | undefined;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-muted">
        {label} <SourceTag source={source} />
      </label>
      <input
        {...register(fieldName)}
        placeholder="provider/model-id"
        className="mt-1 block w-full font-mono text-sm rounded-md border-line-strong shadow-sm focus:border-primary focus:ring-primary"
      />
    </div>
  );
}

export default function ModelsTab({
  register,
  watch,
  setValue,
  models,
  isLoading,
  error,
  onRefresh,
  sources,
}: ModelsTabProps) {
  const [filter, setFilter] = useState<ModelFilter>('all');
  const visibleModels = useMemo(() => {
    if (filter === 'vision') {
      return models.filter((m) => m.supports_vision !== false);
    }
    if (filter === 'strict-json') {
      return models.filter((m) => m.supports_strict_json !== false);
    }
    return models;
  }, [models, filter]);

  const visionPick = watch('vision_model');
  const pricingPick = watch('pricing_model');
  const defaultPick = watch('model');

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted">
          Pick which model handles each role. Vision needs an image-capable
          model; pricing can usually run on a cheaper text-only model.
        </p>
        <button
          type="button"
          onClick={onRefresh}
          className="text-sm font-medium text-primary-hover hover:underline"
        >
          {isLoading ? 'Loading…' : 'Refresh model list'}
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <ModelSelectField
          label="Default model"
          fieldName="model"
          register={register}
          source={sources.model}
        />
        <ModelSelectField
          label="Vision model"
          fieldName="vision_model"
          register={register}
          source={sources.vision_model}
        />
        <ModelSelectField
          label="Pricing model"
          fieldName="pricing_model"
          register={register}
          source={sources.pricing_model}
        />
      </div>

      {error && (
        <div className="text-sm rounded-md bg-danger-subtle text-danger p-3">
          {error}
        </div>
      )}

      <div className="border rounded-md overflow-hidden">
        <div className="bg-surface-muted px-4 py-2 flex items-center gap-3">
          <span className="text-xs font-medium text-muted">Filter:</span>
          {(['all', 'vision', 'strict-json'] as ModelFilter[]).map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => setFilter(f)}
              className={`text-xs px-2 py-1 rounded ${
                filter === f
                  ? 'bg-primary text-white'
                  : 'bg-surface-raised text-muted border border-line'
              }`}
            >
              {f === 'all'
                ? 'All'
                : f === 'vision'
                ? 'Vision-capable'
                : 'Strict JSON'}
            </button>
          ))}
          <span className="ml-auto text-xs text-subtle">
            {visibleModels.length} of {models.length}
          </span>
        </div>
        {models.length === 0 ? (
          <p className="text-sm text-muted p-4">
            No models loaded yet. Click <em>Refresh model list</em> to fetch
            from the configured provider.
          </p>
        ) : (
          <ul className="divide-y divide-line max-h-96 overflow-y-auto">
            {visibleModels.map((m) => (
              <li
                key={m.id}
                className="px-4 py-2 flex items-center justify-between text-sm"
              >
                <div className="flex flex-col">
                  <code className="font-mono text-xs">{m.id}</code>
                  <div className="flex gap-2 mt-1">
                    <CapabilityBadge label="vision" state={m.supports_vision} />
                    <CapabilityBadge
                      label="strict json"
                      state={m.supports_strict_json}
                    />
                    {m.owned_by && (
                      <span className="text-xs text-subtle">
                        {m.owned_by}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex gap-1">
                  <button
                    type="button"
                    onClick={() => setValue('model', m.id, { shouldDirty: true })}
                    className={`text-xs px-2 py-1 rounded border ${
                      defaultPick === m.id
                        ? 'bg-primary text-white border-primary'
                        : 'bg-surface-raised text-muted border-line-strong hover:bg-surface-muted'
                    }`}
                  >
                    Default
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      setValue('vision_model', m.id, { shouldDirty: true })
                    }
                    className={`text-xs px-2 py-1 rounded border ${
                      visionPick === m.id
                        ? 'bg-primary text-white border-primary'
                        : 'bg-surface-raised text-muted border-line-strong hover:bg-surface-muted'
                    }`}
                  >
                    Vision
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      setValue('pricing_model', m.id, { shouldDirty: true })
                    }
                    className={`text-xs px-2 py-1 rounded border ${
                      pricingPick === m.id
                        ? 'bg-primary text-white border-primary'
                        : 'bg-surface-raised text-muted border-line-strong hover:bg-surface-muted'
                    }`}
                  >
                    Pricing
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
