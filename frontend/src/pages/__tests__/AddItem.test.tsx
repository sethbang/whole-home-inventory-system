import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import AddItem from '../AddItem';
import { items, images } from '../../api/client';
import { ApiError } from '../../api/errors';

vi.mock('../../api/client', () => ({
  items: {
    create: vi.fn(),
    getCategories: vi.fn().mockResolvedValue([]),
    getLocations: vi.fn().mockResolvedValue([]),
    lookupBarcode: vi.fn(),
  },
  images: {
    upload: vi.fn(),
  },
}));

vi.mock('../../contexts/useDevMode', () => ({
  useDevMode: () => ({ isDevMode: false }),
}));

// BarcodeScanner is lazy-loaded and touches camera APIs; stub it out so
// the Suspense boundary doesn't stall.
vi.mock('../../components/BarcodeScanner', () => ({
  __esModule: true,
  default: () => <div data-testid="barcode-scanner" />,
}));

const renderAddItem = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AddItem />
      </MemoryRouter>
    </QueryClientProvider>,
  );
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe('AddItem form', () => {
  it('shows validation errors for required fields on empty submit', async () => {
    renderAddItem();
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }));

    expect(await screen.findByText(/name is required/i)).toBeInTheDocument();
    expect(screen.getByText(/category is required/i)).toBeInTheDocument();
    expect(screen.getByText(/location is required/i)).toBeInTheDocument();
    expect(items.create).not.toHaveBeenCalled();
  });

  it('submits a valid item with coerced number/date fields', async () => {
    (items.create as ReturnType<typeof vi.fn>).mockResolvedValue({ id: 'new-1' });

    renderAddItem();
    fireEvent.change(screen.getByLabelText(/^name$/i), {
      target: { value: 'Drill' },
    });
    fireEvent.change(screen.getByLabelText(/^category$/i), {
      target: { value: 'Tools' },
    });
    fireEvent.change(screen.getByLabelText(/^location$/i), {
      target: { value: 'Garage' },
    });
    fireEvent.change(screen.getByLabelText(/purchase price/i), {
      target: { value: '99.50' },
    });
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }));

    await waitFor(() => expect(items.create).toHaveBeenCalledTimes(1));
    const [payload] = (items.create as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(payload.name).toBe('Drill');
    expect(payload.category).toBe('Tools');
    expect(payload.location).toBe('Garage');
    // optionalFloat transform: '99.50' -> 99.5
    expect(payload.purchase_price).toBe(99.5);
    // Empty date fields transform to undefined (not empty strings).
    expect(payload.purchase_date).toBeUndefined();
  });

  it('surfaces ApiError server detail as a server banner', async () => {
    (items.create as ReturnType<typeof vi.fn>).mockRejectedValue(
      new ApiError(400, 'Name is already in use'),
    );

    renderAddItem();
    fireEvent.change(screen.getByLabelText(/^name$/i), {
      target: { value: 'Drill' },
    });
    fireEvent.change(screen.getByLabelText(/^category$/i), {
      target: { value: 'Tools' },
    });
    fireEvent.change(screen.getByLabelText(/^location$/i), {
      target: { value: 'Garage' },
    });
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/name is already in use/i);
  });

  it('rejects a negative purchase price at validation', async () => {
    renderAddItem();
    fireEvent.change(screen.getByLabelText(/^name$/i), {
      target: { value: 'Drill' },
    });
    fireEvent.change(screen.getByLabelText(/^category$/i), {
      target: { value: 'Tools' },
    });
    fireEvent.change(screen.getByLabelText(/^location$/i), {
      target: { value: 'Garage' },
    });
    fireEvent.change(screen.getByLabelText(/purchase price/i), {
      target: { value: '-10' },
    });
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }));

    expect(
      await screen.findByText(/must be a non-negative number/i),
    ).toBeInTheDocument();
    expect(items.create).not.toHaveBeenCalled();
  });

  it('uploads selected images after item creation', async () => {
    (items.create as ReturnType<typeof vi.fn>).mockResolvedValue({ id: 'new-2' });
    (images.upload as ReturnType<typeof vi.fn>).mockResolvedValue({ id: 'img-1' });

    renderAddItem();
    fireEvent.change(screen.getByLabelText(/^name$/i), {
      target: { value: 'Drill' },
    });
    fireEvent.change(screen.getByLabelText(/^category$/i), {
      target: { value: 'Tools' },
    });
    fireEvent.change(screen.getByLabelText(/^location$/i), {
      target: { value: 'Garage' },
    });

    const file = new File([new Uint8Array([1, 2, 3])], 'a.png', {
      type: 'image/png',
    });
    const fileInput = screen.getByLabelText(/^images$/i) as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [file] } });

    fireEvent.click(screen.getByRole('button', { name: /^save$/i }));

    await waitFor(() =>
      expect(images.upload).toHaveBeenCalledWith('new-2', file),
    );
  });
});
