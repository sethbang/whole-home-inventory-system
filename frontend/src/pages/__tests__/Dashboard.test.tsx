import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

import Dashboard from '../Dashboard';
import { items } from '../../api/client';
import {
  filterReducer,
  initialFilterState,
  toSearchFilters,
} from '../Dashboard.filters';
import type { Item, ItemListResponse } from '../../api/types';

// Dashboard imports its helpers from the `api/client` barrel.
vi.mock('../../api/client', () => ({
  items: {
    list: vi.fn(),
    getCategories: vi.fn(),
    getLocations: vi.fn(),
    bulkDelete: vi.fn(),
  },
  ebay: {
    exportItems: vi.fn(),
  },
  facebook: {
    exportItems: vi.fn(),
  },
}));

// DataMigration pulls in apiClient — stub it out so it doesn't matter.
vi.mock('../../components/DataMigration', () => ({
  default: () => <div data-testid="data-migration" />,
}));

function makeItem(overrides: Partial<Item> = {}): Item {
  return {
    id: `id-${Math.random().toString(36).slice(2, 8)}`,
    owner_id: 'owner-1',
    name: 'Hammer',
    category: 'Tools',
    location: 'Garage',
    current_value: 12,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    images: [],
    ...overrides,
  } as Item;
}

function makeListResponse(
  listItems: Item[],
  total?: number,
): ItemListResponse {
  return {
    items: listItems,
    total: total ?? listItems.length,
    page: 1,
    page_size: 20,
  } as ItemListResponse;
}

const hammer = makeItem({ id: 'i1', name: 'Hammer', category: 'Tools' });
const toaster = makeItem({
  id: 'i2',
  name: 'Toaster',
  category: 'Appliances',
});

function renderDashboard() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (items.list as ReturnType<typeof vi.fn>).mockResolvedValue(
      makeListResponse([hammer, toaster]),
    );
    (items.getCategories as ReturnType<typeof vi.fn>).mockResolvedValue([
      'Tools',
      'Appliances',
    ]);
    (items.getLocations as ReturnType<typeof vi.fn>).mockResolvedValue([
      'Garage',
      'Kitchen',
    ]);
    (items.bulkDelete as ReturnType<typeof vi.fn>).mockResolvedValue(
      undefined,
    );
  });

  it('renders the item list from the mocked API', async () => {
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText('Hammer')).toBeInTheDocument();
    });
    expect(screen.getByText('Toaster')).toBeInTheDocument();
  });

  it('passes a search query through to items.list', async () => {
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText('Hammer')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText('Search'), {
      target: { value: 'drill' },
    });

    await waitFor(() => {
      expect(items.list).toHaveBeenCalledWith(
        expect.objectContaining({ query: 'drill', page: 1 }),
      );
    });
  });

  it('passes a category change through to items.list', async () => {
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText('Hammer')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText('Category'), {
      target: { value: 'Tools' },
    });

    await waitFor(() => {
      expect(items.list).toHaveBeenCalledWith(
        expect.objectContaining({ category: 'Tools', page: 1 }),
      );
    });
  });

  it('advances the page when Next is clicked', async () => {
    // total (40) exceeds page_size (20) so pagination renders.
    (items.list as ReturnType<typeof vi.fn>).mockResolvedValue(
      makeListResponse([hammer, toaster], 40),
    );
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText('Hammer')).toBeInTheDocument();
    });

    const nextButtons = screen.getAllByText('Next');
    fireEvent.click(nextButtons[0]);

    await waitFor(() => {
      expect(items.list).toHaveBeenCalledWith(
        expect.objectContaining({ page: 2 }),
      );
    });
  });

  it('opens the delete-confirmation dialog when items are selected', async () => {
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText('Hammer')).toBeInTheDocument();
    });

    // Select a row, then trigger the bulk-delete dialog.
    fireEvent.click(screen.getByLabelText('Select Hammer'));
    fireEvent.click(screen.getByText(/Delete Selected/));

    const dialog = await screen.findByRole('dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(
      screen.getByText('Delete Selected Items'),
    ).toBeInTheDocument();
  });

  it('deletes selected items after confirming in the dialog', async () => {
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText('Hammer')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByLabelText('Select Hammer'));
    fireEvent.click(screen.getByText(/Delete Selected/));

    const dialog = await screen.findByRole('dialog');
    fireEvent.click(
      screen.getByRole('button', { name: 'Delete' }),
    );

    await waitFor(() => {
      expect(items.bulkDelete).toHaveBeenCalledWith(['i1']);
    });
    // The dialog closes only after bulkDelete's promise resolves, so wait
    // for it rather than asserting synchronously (flaky on slow CI).
    await waitFor(() => {
      expect(dialog).not.toBeInTheDocument();
    });
  });

  it('closes the delete dialog on Escape without deleting', async () => {
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText('Hammer')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByLabelText('Select Hammer'));
    fireEvent.click(screen.getByText(/Delete Selected/));
    await screen.findByRole('dialog');

    fireEvent.keyDown(document, { key: 'Escape' });

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
    expect(items.bulkDelete).not.toHaveBeenCalled();
  });

  it('toggles the view-mode buttons with aria-pressed', async () => {
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText('Hammer')).toBeInTheDocument();
    });

    const listBtn = screen.getByRole('button', { name: 'List view' });
    const gridBtn = screen.getByRole('button', { name: 'Grid view' });
    expect(listBtn).toHaveAttribute('aria-pressed', 'true');
    expect(gridBtn).toHaveAttribute('aria-pressed', 'false');

    fireEvent.click(gridBtn);
    expect(gridBtn).toHaveAttribute('aria-pressed', 'true');
    expect(listBtn).toHaveAttribute('aria-pressed', 'false');
  });
});

describe('filterReducer', () => {
  it('starts from the documented defaults', () => {
    expect(initialFilterState).toEqual({
      query: '',
      category: '',
      location: '',
      min_value: undefined,
      max_value: undefined,
      sort_by: '',
      sort_desc: false,
      page: 1,
      page_size: 20,
    });
  });

  it('SET_QUERY updates the query and resets page to 1', () => {
    const start = { ...initialFilterState, page: 3 };
    const next = filterReducer(start, { type: 'SET_QUERY', value: 'drill' });
    expect(next.query).toBe('drill');
    expect(next.page).toBe(1);
  });

  it('SET_CATEGORY updates the category and resets page', () => {
    const start = { ...initialFilterState, page: 4 };
    const next = filterReducer(start, {
      type: 'SET_CATEGORY',
      value: 'Tools',
    });
    expect(next.category).toBe('Tools');
    expect(next.page).toBe(1);
  });

  it('SET_SORT updates both sort fields at once', () => {
    const next = filterReducer(initialFilterState, {
      type: 'SET_SORT',
      sort_by: 'name',
      sort_desc: true,
    });
    expect(next.sort_by).toBe('name');
    expect(next.sort_desc).toBe(true);
  });

  it('SET_PAGE changes the page without touching other fields', () => {
    const start = { ...initialFilterState, query: 'kept' };
    const next = filterReducer(start, { type: 'SET_PAGE', value: 5 });
    expect(next.page).toBe(5);
    expect(next.query).toBe('kept');
  });

  it('RESET returns to the initial state', () => {
    const dirty = filterReducer(
      { ...initialFilterState, query: 'x', page: 9 },
      { type: 'RESET' },
    );
    expect(dirty).toEqual(initialFilterState);
  });

  it('toSearchFilters mirrors the filter state', () => {
    const state = { ...initialFilterState, query: 'hammer', page: 2 };
    expect(toSearchFilters(state)).toEqual({
      query: 'hammer',
      category: '',
      location: '',
      min_value: undefined,
      max_value: undefined,
      sort_by: '',
      sort_desc: false,
      page: 2,
      page_size: 20,
    });
  });
});
