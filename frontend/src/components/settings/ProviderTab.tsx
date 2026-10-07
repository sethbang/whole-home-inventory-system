/**
 * Provider tab — base URL, API key (masked display + replace flow),
 * request timeout, and the response-healing toggle.
 */

import { useForm, type FieldErrors } from 'react-hook-form';

import type { LLMConfigRead } from '../../api/types';
import { SourceTag } from './badges';
import type { FormValues } from './types';

type RegisterFn = ReturnType<typeof useForm<FormValues>>['register'];
type SetValueFn = ReturnType<typeof useForm<FormValues>>['setValue'];

interface ProviderTabProps {
  register: RegisterFn;
  setValue: SetValueFn;
  errors: FieldErrors<FormValues>;
  cfg: LLMConfigRead;
  sources: Record<string, string>;
  apiKeyDirty: boolean;
  onBeginApiKeyEdit: () => void;
  onCancelApiKeyEdit: () => void;
  onClearApiKey: () => void;
}

export default function ProviderTab({
  register,
  setValue,
  errors,
  cfg,
  sources,
  apiKeyDirty,
  onBeginApiKeyEdit,
  onCancelApiKeyEdit,
  onClearApiKey,
}: ProviderTabProps) {
  return (
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
                onBeginApiKeyEdit();
                setValue('api_key', '');
              }}
              className="text-sm font-medium text-primary-hover hover:underline"
            >
              {cfg.api_key_set ? 'Replace key' : 'Set key'}
            </button>
            {cfg.api_key_set && (
              <button
                type="button"
                onClick={onClearApiKey}
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
                onCancelApiKeyEdit();
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
            Timeout (seconds) <SourceTag source={sources.timeout_seconds} />
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
  );
}
