import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

import Browse from '../Browse';
import { items } from '../../api/items';
import type { Item } from '../../api/types';

vi.mock('../../api/items', () => ({
  items: {
    list: vi.fn(),
    getCategories: vi.fn(),
    getLocationCounts: vi.fn(),
  },
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

const garageItem = makeItem({ id: 'i1', name: 'Hammer', location: 'Garage' });
const kitchenItem = makeItem({ id: 'i2', name: 'Toaster', location: 'Kitchen' });

function renderBrowse() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <Browse />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Browse', () => {
  beforeEach(() => {
    vi.mocked(items.getCategories).mockResolvedValue(['Tools', 'Kitchen']);
    vi.mocked(items.getLocationCounts).mockResolvedValue([
      { location: 'Garage', count: 1 },
      { location: 'Kitchen', count: 1 },
    ]);
    vi.mocked(items.list).mockResolvedValue({
      items: [garageItem, kitchenItem],
      total: 2,
      page: 1,
      page_size: 24,
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders rooms sidebar with counts and All total', async () => {
    renderBrowse();
    await waitFor(() => {
      expect(screen.getAllByText('Garage')[0]).toBeInTheDocument();
      expect(screen.getAllByText('Kitchen')[0]).toBeInTheDocument();
    });
    // The "All" entry sums counts: 1 + 1 = 2.
    expect(screen.getByRole('button', { name: /All\s*2/ })).toBeInTheDocument();
  });

  it('filters by location when a room is clicked', async () => {
    renderBrowse();
    await waitFor(() => {
      expect(items.list).toHaveBeenCalled();
    });

    vi.mocked(items.list).mockResolvedValueOnce({
      items: [garageItem],
      total: 1,
      page: 1,
      page_size: 24,
    });

    // Click the desktop sidebar's "Garage" button. The room buttons come
    // from the separate location-counts query, so wait for them to render
    // rather than assuming it resolved alongside items.list.
    const garageButtons = await screen.findAllByRole('button', {
      name: /Garage\s*1/,
    });
    fireEvent.click(garageButtons[0]);

    await waitFor(() => {
      expect(items.list).toHaveBeenLastCalledWith(
        expect.objectContaining({ location: 'Garage', page: 1 }),
      );
    });
  });

  it('debounces the search input before refetching', async () => {
    renderBrowse();
    await waitFor(() => {
      expect(items.list).toHaveBeenCalled();
    });

    const search = screen.getByLabelText('Search items') as HTMLInputElement;
    fireEvent.change(search, { target: { value: 'd' } });
    fireEvent.change(search, { target: { value: 'dr' } });
    fireEvent.change(search, { target: { value: 'drill' } });

    // After the 250ms debounce window, list() should be called with the
    // final coalesced query — not once per keystroke.
    await waitFor(
      () => {
        expect(items.list).toHaveBeenLastCalledWith(
          expect.objectContaining({ query: 'drill', page: 1 }),
        );
      },
      { timeout: 1500 },
    );
  });

  it('toggles between card and list view', async () => {
    renderBrowse();
    await waitFor(() => {
      expect(screen.getByTestId('browse-card-grid')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByLabelText('List view'));
    expect(screen.getByTestId('browse-list')).toBeInTheDocument();
    expect(screen.queryByTestId('browse-card-grid')).toBeNull();

    fireEvent.click(screen.getByLabelText('Card view'));
    expect(screen.getByTestId('browse-card-grid')).toBeInTheDocument();
  });

  it('shows the empty state when no items match', async () => {
    vi.mocked(items.list).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 24,
    });
    renderBrowse();
    await waitFor(() => {
      expect(screen.getByText('No items match these filters.')).toBeInTheDocument();
    });
  });
});
