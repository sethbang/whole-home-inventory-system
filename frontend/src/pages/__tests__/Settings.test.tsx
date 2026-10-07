import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import SettingsPage from '../Settings';
import { llmConfig } from '../../api/llmConfig';
import type {
  LLMConfigRead,
  LLMModelListResponse,
  LLMTestResponse,
  LLMVisionTestResponse,
} from '../../api/types';

// Mock the LLM operator-config API module Settings talks to.
vi.mock('../../api/llmConfig', () => ({
  llmConfig: {
    get: vi.fn(),
    update: vi.fn(),
    listModels: vi.fn(),
    testQuick: vi.fn(),
    testVision: vi.fn(),
  },
}));

const mockConfig: LLMConfigRead = {
  base_url: 'https://openrouter.ai/api/v1',
  api_key_set: true,
  api_key_last4: 'cd34',
  model: 'openai/gpt-4o-mini',
  vision_model: 'openai/gpt-4o',
  pricing_model: 'openai/gpt-4o-mini',
  timeout_seconds: 90,
  response_healing: true,
  vision_enabled: true,
  pricing_enabled: false,
  vision_daily_cap_usd: 5,
  pricing_daily_cap_usd: 5,
  sources: {
    base_url: 'db',
    api_key: 'db',
    model: 'env',
  },
  today_vision_cost_usd: 0.1234,
  today_pricing_cost_usd: 0,
};

const mockModels: LLMModelListResponse = {
  models: [
    {
      id: 'openai/gpt-4o',
      owned_by: 'openai',
      supports_vision: true,
      supports_strict_json: true,
    },
    {
      id: 'meta/llama-3',
      owned_by: 'meta',
      supports_vision: false,
      supports_strict_json: null,
    },
  ],
};

const mockQuickResult: LLMTestResponse = {
  ok: true,
  base_url: 'https://openrouter.ai/api/v1',
  model: 'openai/gpt-4o-mini',
  detail: 'All configured models exist.',
  checks: { default_model: true, vision_model: true },
};

const mockVisionResult: LLMVisionTestResponse = {
  ok: true,
  model: 'openai/gpt-4o',
  detail: 'Vision round-trip succeeded.',
  parsed_response: { name: 'test' },
  usage: { prompt_tokens: 100, completion_tokens: 20 },
  cost_usd: 0.0012,
};

const get = llmConfig.get as ReturnType<typeof vi.fn>;
const update = llmConfig.update as ReturnType<typeof vi.fn>;
const listModels = llmConfig.listModels as ReturnType<typeof vi.fn>;
const testQuick = llmConfig.testQuick as ReturnType<typeof vi.fn>;
const testVision = llmConfig.testVision as ReturnType<typeof vi.fn>;

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    get.mockResolvedValue(mockConfig);
    update.mockResolvedValue(mockConfig);
    listModels.mockResolvedValue(mockModels);
    testQuick.mockResolvedValue(mockQuickResult);
    testVision.mockResolvedValue(mockVisionResult);
  });

  it('renders the provider config form from a mocked /api/llm-config response', async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Settings')).toBeInTheDocument();
    });

    // Base URL field is seeded from the fetched config.
    const baseUrl = screen.getByPlaceholderText(
      'https://openrouter.ai/api/v1',
    ) as HTMLInputElement;
    expect(baseUrl).toHaveValue('https://openrouter.ai/api/v1');
    expect(get).toHaveBeenCalled();
  });

  it('shows the masked API key and reveals an edit input on Replace key', async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/••••••••cd34/)).toBeInTheDocument();
    });

    // No password input until the operator opts to replace the key.
    expect(
      screen.queryByPlaceholderText('paste new key'),
    ).not.toBeInTheDocument();

    fireEvent.click(screen.getByText('Replace key'));

    const keyInput = screen.getByPlaceholderText('paste new key');
    expect(keyInput).toBeInTheDocument();
    expect(keyInput).toHaveAttribute('type', 'password');
    // Masked display is gone once editing.
    expect(screen.queryByText(/••••••••cd34/)).not.toBeInTheDocument();
  });

  it('switches tabs and renders each section', async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Settings')).toBeInTheDocument();
    });

    // Budget tab.
    fireEvent.click(screen.getByRole('button', { name: 'Budget' }));
    expect(screen.getByText(/Vision daily cap/)).toBeInTheDocument();

    // Models tab.
    fireEvent.click(screen.getByRole('button', { name: 'Models' }));
    expect(
      screen.getByRole('button', { name: 'Refresh model list' }),
    ).toBeInTheDocument();

    // Test tab.
    fireEvent.click(screen.getByRole('button', { name: 'Test' }));
    expect(
      screen.getByRole('button', { name: 'Run quick test' }),
    ).toBeInTheDocument();
  });

  it('submits a changed config and calls the update API', async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Settings')).toBeInTheDocument();
    });

    const baseUrl = screen.getByPlaceholderText(
      'https://openrouter.ai/api/v1',
    );
    await act(async () => {
      fireEvent.change(baseUrl, {
        target: { value: 'https://example.com/v1' },
      });
    });

    await act(async () => {
      fireEvent.click(screen.getByText('Save changes'));
    });

    await waitFor(() => {
      expect(update).toHaveBeenCalledWith(
        expect.objectContaining({ base_url: 'https://example.com/v1' }),
      );
    });
    await waitFor(() => {
      expect(screen.getByText('Saved.')).toBeInTheDocument();
    });
  });

  it('does not call update when there are no changes to save', async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Settings')).toBeInTheDocument();
    });

    // Save button is disabled while the form is pristine.
    expect(screen.getByText('Save changes')).toBeDisabled();
    expect(update).not.toHaveBeenCalled();
  });

  it('runs the quick connection test and renders its result', async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Settings')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: 'Test' }));

    await act(async () => {
      fireEvent.click(screen.getByText('Run quick test'));
    });

    await waitFor(() => {
      expect(testQuick).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(
        screen.getByText(/All configured models exist\./),
      ).toBeInTheDocument();
    });
    expect(screen.getByText(/✓ Passed/)).toBeInTheDocument();
  });

  it('runs the vision test and renders its result', async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Settings')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: 'Test' }));

    await act(async () => {
      fireEvent.click(
        screen.getByRole('button', { name: 'Run vision test' }),
      );
    });

    await waitFor(() => {
      expect(testVision).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(
        screen.getByText(/Vision round-trip succeeded\./),
      ).toBeInTheDocument();
    });
  });

  it('fetches and lists provider models when Refresh is clicked', async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Settings')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: 'Models' }));
    expect(screen.getByText(/No models loaded yet/)).toBeInTheDocument();

    await act(async () => {
      fireEvent.click(
        screen.getByRole('button', { name: 'Refresh model list' }),
      );
    });

    await waitFor(() => {
      expect(listModels).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(screen.getByText('openai/gpt-4o')).toBeInTheDocument();
    });
    expect(screen.getByText('meta/llama-3')).toBeInTheDocument();
  });
});
