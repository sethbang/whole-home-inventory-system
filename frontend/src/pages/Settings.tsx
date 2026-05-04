/**
 * Operator LLM-config dashboard (v3.2).
 *
 * Admin-only. Lets a household admin edit the LLM provider end-to-end:
 * base URL, API key (encrypted at rest), default/vision/pricing model
 * pickers, daily cost caps, feature flags, and a tiered Test panel
 * (quick vs deep).
 */

import { useEffect, useMemo, useState } from 'react';
import { useForm, type SubmitHandler } from 'react-hook-form';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { apiErrorMessage } from '../api/errors';
import { llmConfig } from '../api/llmConfig';
import { queryKeys } from '../api/queryKeys';
import type {
  LLMConfigRead,
  LLMConfigUpdate,
  LLMModelEntry,
  LLMTestResponse,
  LLMVisionTestResponse,
} from '../api/types';

type TabId = 'provider' | 'models' | 'budget' | 'test';

const TABS: Array<{ id: TabId; label: string }> = [
  { id: 'provider', label: 'Provider' },
  { id: 'models', label: 'Models' },
  { id: 'budget', label: 'Budget' },
  { id: 'test', label: 'Test' },
];

interface FormValues {
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

function formDefaults(cfg: LLMConfigRead | undefined): FormValues {
  return {
    base_url: cfg?.base_url ?? '',
    api_key: '',
    model: cfg?.model ?? '',
    vision_model: cfg?.vision_model ?? '',
    pricing_model: cfg?.pricing_model ?? '',
    timeout_seconds: cfg?.timeout_seconds ?? 90,
    response_healing: cfg?.response_healing ?? true,
    vision_enabled: cfg?.vision_enabled ?? false,
    pricing_enabled: cfg?.pricing_enabled ?? false,
    vision_daily_cap_usd: cfg?.vision_daily_cap_usd ?? 5,
    pricing_daily_cap_usd: cfg?.pricing_daily_cap_usd ?? 5,
  };
}

function buildUpdatePayload(
  values: FormValues,
  initial: LLMConfigRead,
  apiKeyDirty: boolean,
): LLMConfigUpdate {
  const out: LLMConfigUpdate = {};
  if (values.base_url !== initial.base_url) out.base_url = values.base_url;
  if (apiKeyDirty) out.api_key = values.api_key;
  if (values.model !== initial.model) out.model = values.model;
  if (values.vision_model !== initial.vision_model) {
    out.vision_model = values.vision_model;
  }
  if (values.pricing_model !== initial.pricing_model) {
    out.pricing_model = values.pricing_model;
  }
  if (values.timeout_seconds !== initial.timeout_seconds) {
    out.timeout_seconds = values.timeout_seconds;
  }
  if (values.response_healing !== initial.response_healing) {
    out.response_healing = values.response_healing;
  }
  if (values.vision_enabled !== initial.vision_enabled) {
    out.vision_enabled = values.vision_enabled;
  }
  if (values.pricing_enabled !== initial.pricing_enabled) {
    out.pricing_enabled = values.pricing_enabled;
  }
  if (values.vision_daily_cap_usd !== initial.vision_daily_cap_usd) {
    out.vision_daily_cap_usd = values.vision_daily_cap_usd;
  }
  if (values.pricing_daily_cap_usd !== initial.pricing_daily_cap_usd) {
    out.pricing_daily_cap_usd = values.pricing_daily_cap_usd;
  }
  return out;
}

function CapabilityBadge({
  label,
  state,
}: {
  label: string;
  state: boolean | null | undefined;
}) {
  if (state === true) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-success-subtle text-success">
        ✓ {label}
      </span>
    );
  }
  if (state === false) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-danger-subtle text-danger">
        ✗ {label}
      </span>
    );
  }
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-surface-muted text-muted"
      title="Provider didn't expose a capability flag for this model. Use the Test tab to verify."
    >
      ? {label}
    </span>
  );
}

function SourceTag({ source }: { source: string | undefined }) {
  if (source === 'db') {
    return (
      <span className="text-[11px] uppercase tracking-wide text-primary-hover">
        ● set in app
      </span>
    );
  }
  if (source === 'env') {
    return (
      <span className="text-[11px] uppercase tracking-wide text-subtle">
        ○ from .env
      </span>
    );
  }
  return (
    <span className="text-[11px] uppercase tracking-wide text-subtle">
      ○ default
    </span>
  );
}

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<TabId>('provider');
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [statusKind, setStatusKind] = useState<'ok' | 'error' | null>(null);
  const [apiKeyDirty, setApiKeyDirty] = useState(false);

  const configQuery = useQuery({
    queryKey: queryKeys.llmConfig.detail(),
    queryFn: llmConfig.get,
  });

  const modelsQuery = useQuery({
    queryKey: queryKeys.llmConfig.models(),
    queryFn: llmConfig.listModels,
    enabled: false, // user-triggered (Models tab "Refresh" button)
    retry: false,
  });

  const updateMutation = useMutation({
    mutationFn: (payload: LLMConfigUpdate) => llmConfig.update(payload),
    onSuccess: (next) => {
      queryClient.setQueryData(queryKeys.llmConfig.detail(), next);
      queryClient.invalidateQueries({ queryKey: queryKeys.llmConfig.models() });
      setStatusMessage('Saved.');
      setStatusKind('ok');
      setApiKeyDirty(false);
    },
    onError: (err) => {
      setStatusMessage(apiErrorMessage(err));
      setStatusKind('error');
    },
  });

  const quickTestMutation = useMutation({
    mutationFn: (body?: LLMConfigUpdate | null) => llmConfig.testQuick(body),
  });

  const visionTestMutation = useMutation({
    mutationFn: (body?: LLMConfigUpdate | null) => llmConfig.testVision(body),
  });

  const initialDefaults = useMemo(
    () => formDefaults(configQuery.data),
    [configQuery.data],
  );

  const {
    register,
    handleSubmit,
    reset,
    watch,
    setValue,
    formState: { errors, isDirty },
  } = useForm<FormValues>({ defaultValues: initialDefaults });

  // Re-seed the form when the GET completes / refreshes.
  useEffect(() => {
    reset(initialDefaults);
    setApiKeyDirty(false);
  }, [initialDefaults, reset]);

  const onSubmit: SubmitHandler<FormValues> = (values) => {
    if (!configQuery.data) return;
    setStatusMessage(null);
    setStatusKind(null);
    const payload = buildUpdatePayload(values, configQuery.data, apiKeyDirty);
    if (Object.keys(payload).length === 0) {
      setStatusMessage('No changes to save.');
      setStatusKind('ok');
      return;
    }
    updateMutation.mutate(payload);
  };

  if (configQuery.isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary" />
      </div>
    );
  }

  if (configQuery.isError) {
    return (
      <div className="rounded-md bg-danger-subtle p-4 text-sm text-danger">
        Could not load settings: {apiErrorMessage(configQuery.error)}
      </div>
    );
  }

  const cfg = configQuery.data!;
  const sources = (cfg.sources ?? {}) as Record<string, string>;

  return (
    <div className="max-w-4xl mx-auto">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold text-fg">Settings</h1>
        <p className="text-sm text-muted mt-1">
          LLM provider configuration. Changes go live without a restart.
          The API key is encrypted at rest with a key derived from{' '}
          <code className="bg-surface-muted px-1 rounded">SECRET_KEY</code>.
        </p>
      </header>

      <div className="bg-surface-raised shadow rounded-lg overflow-hidden">
        <div className="border-b border-line">
          <nav className="-mb-px flex" aria-label="Tabs">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                type="button"
                className={`whitespace-nowrap py-3 px-4 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-primary text-primary-hover'
                    : 'border-transparent text-subtle hover:text-muted hover:border-line-strong'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-6">
          {activeTab === 'provider' && (
            <div className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-muted">
                  Base URL <SourceTag source={sources.base_url} />
                </label>
                <input
                  {...register('base_url')}
                  placeholder="https://openrouter.ai/api/v1"
                  className="mt-1 block w-full rounded-md border-line-strong shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
                />
                {errors.base_url && (
                  <p className="mt-1 text-xs text-danger">{errors.base_url.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-muted">
                  API Key <SourceTag source={sources.api_key} />
                </label>
                {!apiKeyDirty ? (
                  <div className="mt-1 flex items-center gap-3">
                    <code className="font-mono text-sm bg-surface-muted px-3 py-2 rounded border border-line text-muted">
                      {cfg.api_key_set
                        ? `••••••••${cfg.api_key_last4 ?? ''}`
                        : '(not set)'}
                    </code>
                    <button
                      type="button"
                      onClick={() => {
                        setApiKeyDirty(true);
                        setValue('api_key', '');
                      }}
                      className="text-sm font-medium text-primary-hover hover:underline"
                    >
                      {cfg.api_key_set ? 'Replace key' : 'Set key'}
                    </button>
                    {cfg.api_key_set && (
                      <button
                        type="button"
                        onClick={() => updateMutation.mutate({ api_key: '' })}
                        className="text-sm font-medium text-subtle hover:underline"
                      >
                        Clear (use env)
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="mt-1 flex items-center gap-2">
                    <input
                      {...register('api_key')}
                      type="password"
                      autoComplete="new-password"
                      placeholder="paste new key"
                      className="block w-full rounded-md border-line-strong shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
                    />
                    <button
                      type="button"
                      onClick={() => {
                        setApiKeyDirty(false);
                        setValue('api_key', '');
                      }}
                      className="text-sm text-subtle hover:underline"
                    >
                      Cancel
                    </button>
                  </div>
                )}
                <p className="mt-1 text-xs text-subtle">
                  Encrypted at rest. Never returned to the browser after save.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-muted">
                    Timeout (seconds){' '}
                    <SourceTag source={sources.timeout_seconds} />
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={600}
                    {...register('timeout_seconds', { valueAsNumber: true })}
                    className="mt-1 block w-full rounded-md border-line-strong shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
                  />
                </div>
                <div className="flex items-center sm:justify-end">
                  <label className="inline-flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      {...register('response_healing')}
                      className="h-4 w-4 rounded border-line-strong text-primary focus:ring-primary"
                    />
                    Response healing (OpenRouter only)
                  </label>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'models' && (
            <ModelsTab
              register={register}
              watch={watch}
              setValue={setValue}
              models={modelsQuery.data?.models ?? []}
              isLoading={modelsQuery.isFetching}
              error={modelsQuery.isError ? apiErrorMessage(modelsQuery.error) : null}
              onRefresh={() => modelsQuery.refetch()}
              sources={sources}
            />
          )}

          {activeTab === 'budget' && (
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
          )}

          {activeTab === 'test' && (
            <TestTab
              quickResult={quickTestMutation.data ?? null}
              quickIsPending={quickTestMutation.isPending}
              quickError={
                quickTestMutation.isError
                  ? apiErrorMessage(quickTestMutation.error)
                  : null
              }
              onQuick={() => quickTestMutation.mutate(null)}
              visionResult={visionTestMutation.data ?? null}
              visionIsPending={visionTestMutation.isPending}
              visionError={
                visionTestMutation.isError
                  ? apiErrorMessage(visionTestMutation.error)
                  : null
              }
              onVision={() => visionTestMutation.mutate(null)}
            />
          )}

          {statusMessage && (
            <div
              className={`text-sm rounded-md p-3 ${
                statusKind === 'error'
                  ? 'bg-danger-subtle text-danger'
                  : 'bg-success-subtle text-success'
              }`}
            >
              {statusMessage}
            </div>
          )}

          {activeTab !== 'test' && (
            <div className="flex items-center gap-3 pt-4 border-t border-line">
              <button
                type="submit"
                disabled={updateMutation.isPending || (!isDirty && !apiKeyDirty)}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
              >
                {updateMutation.isPending ? 'Saving…' : 'Save changes'}
              </button>
              <button
                type="button"
                onClick={() => {
                  reset(initialDefaults);
                  setApiKeyDirty(false);
                  setStatusMessage(null);
                  setStatusKind(null);
                }}
                disabled={!isDirty && !apiKeyDirty}
                className="inline-flex items-center px-4 py-2 border border-line-strong text-sm font-medium rounded-md text-muted bg-surface-raised hover:bg-surface-muted disabled:opacity-50"
              >
                Discard
              </button>
            </div>
          )}
        </form>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab components — kept inline for now; if Settings grows, extract.
// ---------------------------------------------------------------------------

interface ModelsTabProps {
  register: ReturnType<typeof useForm<FormValues>>['register'];
  watch: ReturnType<typeof useForm<FormValues>>['watch'];
  setValue: ReturnType<typeof useForm<FormValues>>['setValue'];
  models: LLMModelEntry[];
  isLoading: boolean;
  error: string | null;
  onRefresh: () => void;
  sources: Record<string, string>;
}

type ModelFilter = 'all' | 'vision' | 'strict-json';

function ModelsTab({
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

function ModelSelectField({
  label,
  fieldName,
  register,
  source,
}: {
  label: string;
  fieldName: 'model' | 'vision_model' | 'pricing_model';
  register: ReturnType<typeof useForm<FormValues>>['register'];
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

function TestTab({
  quickResult,
  quickIsPending,
  quickError,
  onQuick,
  visionResult,
  visionIsPending,
  visionError,
  onVision,
}: {
  quickResult: LLMTestResponse | null;
  quickIsPending: boolean;
  quickError: string | null;
  onQuick: () => void;
  visionResult: LLMVisionTestResponse | null;
  visionIsPending: boolean;
  visionError: string | null;
  onVision: () => void;
}) {
  return (
    <div className="space-y-6">
      <section>
        <h3 className="text-sm font-medium text-fg">Quick test</h3>
        <p className="text-sm text-muted mt-1">
          Lists the provider's models and confirms the configured Default,
          Vision, and Pricing models all exist. Doesn't spend tokens.
        </p>
        <button
          type="button"
          onClick={onQuick}
          disabled={quickIsPending}
          className="mt-2 inline-flex items-center px-3 py-1.5 border border-line-strong text-sm font-medium rounded-md text-muted bg-surface-raised hover:bg-surface-muted disabled:opacity-50"
        >
          {quickIsPending ? 'Running…' : 'Run quick test'}
        </button>
        {quickError && (
          <pre className="mt-2 text-xs whitespace-pre-wrap rounded-md bg-danger-subtle text-danger p-3">
            {quickError}
          </pre>
        )}
        {quickResult && <TestResultPanel result={quickResult} kind="quick" />}
      </section>

      <section className="border-t pt-5">
        <h3 className="text-sm font-medium text-fg">Run vision test</h3>
        <p className="text-sm text-muted mt-1">
          Sends a tiny embedded test image through the configured Vision
          model with a strict JSON schema. Costs a small amount of tokens
          but proves end-to-end vision + strict-schema support.
        </p>
        <button
          type="button"
          onClick={onVision}
          disabled={visionIsPending}
          className="mt-2 inline-flex items-center px-3 py-1.5 border border-line-strong text-sm font-medium rounded-md text-muted bg-surface-raised hover:bg-surface-muted disabled:opacity-50"
        >
          {visionIsPending ? 'Running…' : 'Run vision test'}
        </button>
        {visionError && (
          <pre className="mt-2 text-xs whitespace-pre-wrap rounded-md bg-danger-subtle text-danger p-3">
            {visionError}
          </pre>
        )}
        {visionResult && (
          <TestResultPanel result={visionResult} kind="vision" />
        )}
      </section>
    </div>
  );
}

function TestResultPanel({
  result,
  kind,
}: {
  result: LLMTestResponse | LLMVisionTestResponse;
  kind: 'quick' | 'vision';
}) {
  const ok = result.ok;
  return (
    <div
      className={`mt-3 rounded-md p-3 text-sm ${
        ok ? 'bg-success-subtle text-success' : 'bg-danger-subtle text-danger'
      }`}
    >
      <div className="font-medium">
        {ok ? '✓ Passed' : '✗ Failed'} — {result.model}
      </div>
      {result.detail && <div className="mt-1 text-xs">{result.detail}</div>}
      {kind === 'quick' && 'checks' in result && result.checks && (
        <pre className="mt-2 text-xs bg-surface-raised/50 rounded p-2 whitespace-pre-wrap">
          {JSON.stringify(result.checks, null, 2)}
        </pre>
      )}
      {kind === 'vision' && 'parsed_response' in result && result.parsed_response && (
        <pre className="mt-2 text-xs bg-surface-raised/50 rounded p-2 whitespace-pre-wrap">
          {JSON.stringify(result.parsed_response, null, 2)}
        </pre>
      )}
      {kind === 'vision' && 'usage' in result && result.usage && (
        <p className="mt-1 text-xs">
          Tokens in: {Number(result.usage.prompt_tokens ?? 0)} · out:{' '}
          {Number(result.usage.completion_tokens ?? 0)} · cost: $
          {(result.cost_usd ?? 0).toFixed(6)}
        </p>
      )}
    </div>
  );
}
