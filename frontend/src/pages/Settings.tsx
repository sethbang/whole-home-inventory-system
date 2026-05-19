/**
 * Operator LLM-config dashboard (v3.2).
 *
 * Admin-only. Lets a household admin edit the LLM provider end-to-end:
 * base URL, API key (encrypted at rest), default/vision/pricing model
 * pickers, daily cost caps, feature flags, and a tiered Test panel
 * (quick vs deep).
 *
 * This page is a thin orchestrator: it owns data fetching, tab state,
 * and form wiring, then delegates rendering to the tab subcomponents
 * under ``src/components/settings/``.
 */

import { useEffect, useMemo, useState } from 'react';
import { useForm, type SubmitHandler } from 'react-hook-form';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { apiErrorMessage } from '../api/errors';
import { llmConfig } from '../api/llmConfig';
import { queryKeys } from '../api/queryKeys';
import type { LLMConfigRead, LLMConfigUpdate } from '../api/types';
import BudgetTab from '../components/settings/BudgetTab';
import ModelsTab from '../components/settings/ModelsTab';
import ProviderTab from '../components/settings/ProviderTab';
import TestTab from '../components/settings/TestTab';
import type { FormValues, TabId } from '../components/settings/types';

const TABS: Array<{ id: TabId; label: string }> = [
  { id: 'provider', label: 'Provider' },
  { id: 'models', label: 'Models' },
  { id: 'budget', label: 'Budget' },
  { id: 'test', label: 'Test' },
];

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
          <nav className="-mb-px flex" aria-label="Settings sections">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                type="button"
                aria-current={activeTab === tab.id ? 'page' : undefined}
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
            <ProviderTab
              register={register}
              setValue={setValue}
              errors={errors}
              cfg={cfg}
              sources={sources}
              apiKeyDirty={apiKeyDirty}
              onBeginApiKeyEdit={() => setApiKeyDirty(true)}
              onCancelApiKeyEdit={() => setApiKeyDirty(false)}
              onClearApiKey={() => updateMutation.mutate({ api_key: '' })}
            />
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
            <BudgetTab register={register} cfg={cfg} sources={sources} />
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
