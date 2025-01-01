import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ItemDetail from '../ItemDetail';
import { items, images, ebay } from '../../api/client';
import type { Item, EbayCategoryResponse } from '../../api/client';

// Mock the API client modules
jest.mock('../../api/client', () => ({
  items: {
    get: jest.fn(),
    update: jest.fn(),
    delete: jest.fn(),
    getCategories: jest.fn(),
    getLocations: jest.fn(),
  },
  images: {
    upload: jest.fn(),
    delete: jest.fn(),
  },
  ebay: {
    getCategories: jest.fn(),
    updateFields: jest.fn(),
  },
}));

const mockItem: Item = {
  id: '123',
  name: 'Test Item',
  category: 'Electronics',
  location: 'Office',
  brand: 'Test Brand',
  model_number: 'TEST123',
  serial_number: 'SN123',
  purchase_date: '2023-01-01T00:00:00Z',
  purchase_price: 100,
  current_value: 80,
  warranty_expiration: '2024-01-01T00:00:00Z',
  notes: 'Test notes',
  custom_fields: {
    ebay: {
      category_id: 'ebay123',
      condition: 'NEW',
      listing_format: 'FIXED_PRICE',
    },
  },
  created_at: '2023-01-01T00:00:00Z',
  updated_at: '2023-01-01T00:00:00Z',
  images: [],
};

const mockCategories = ['Electronics', 'Furniture', 'Kitchen'];
const mockLocations = ['Office', 'Living Room', 'Garage'];

const mockEbayCategoryResponse: EbayCategoryResponse = {
  categories: [
    {
      id: 'ebay123',
      name: 'Electronics',
      subcategories: [
        { id: 'ebay456', name: 'Computers' },
      ],
    },
  ],
  suggested_category: {
    id: 'ebay123',
    name: 'Electronics',
  },
};

describe('ItemDetail', () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();

    // Setup default mock responses
    (items.get as jest.Mock).mockResolvedValue(mockItem);
    (items.getCategories as jest.Mock).mockResolvedValue(mockCategories);
    (items.getLocations as jest.Mock).mockResolvedValue(mockLocations);
    (ebay.getCategories as jest.Mock).mockResolvedValue(mockEbayCategoryResponse);
  });

  const renderComponent = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/items/123']}>
          <Routes>
            <Route path="/items/:id" element={<ItemDetail />} />
            <Route path="/" element={<div>Home</div>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );
  };

  it('loads and displays item details', async () => {
    renderComponent();

    // Wait for item data to load
    await waitFor(() => {
      expect(screen.getByText('Edit Item: Test Item')).toBeInTheDocument();
    });

    // Check if form fields are populated
    expect(screen.getByLabelText(/^name$/i)).toHaveValue('Test Item');
    
    // Use getByRole to find the category select element
    const categorySelect = screen.getByRole('combobox', { name: /^category$/i });
    expect(categorySelect).toHaveValue('Electronics');
    
    // Use getByRole to find the location select element
    const locationSelect = screen.getByRole('combobox', { name: /^location$/i });
    expect(locationSelect).toHaveValue('Office');
  });

  it('displays eBay fields section', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('eBay Listing Details')).toBeInTheDocument();
    });

    // Check if eBay fields are populated
    expect(screen.getByLabelText(/listing format/i)).toHaveValue('FIXED_PRICE');
    expect(screen.getByLabelText(/condition/i)).toHaveValue('NEW');
  });

  it('handles eBay category lookup', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Look Up')).toBeInTheDocument();
    });

    // Click the category lookup button
    await act(async () => {
      fireEvent.click(screen.getByText('Look Up'));
    });

    // Wait for the API call and state updates
    await waitFor(() => {
      expect(ebay.getCategories).toHaveBeenCalledWith('123');
    });

    // Wait for the category to be updated
    await waitFor(() => {
      const categoryInput = screen.getByPlaceholderText('eBay Category ID');
      expect(categoryInput).toHaveValue('ebay123');
    });
  });

  it('updates eBay fields', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByLabelText(/listing format/i)).toBeInTheDocument();
    });

    // Change listing format
    await act(async () => {
      fireEvent.change(screen.getByLabelText(/listing format/i), {
        target: { value: 'AUCTION' }
      });
    });

    // Verify the API was called with updated fields
    await waitFor(() => {
      expect(ebay.updateFields).toHaveBeenCalledWith('123', expect.objectContaining({
        listing_format: 'AUCTION'
      }));
    });
  });

  it('saves item with eBay fields', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Save')).toBeInTheDocument();
    });

    // Update some fields
    await act(async () => {
      fireEvent.change(screen.getByLabelText(/^name$/i), {
        target: { value: 'Updated Item' }
      });

      fireEvent.change(screen.getByLabelText(/listing format/i), {
        target: { value: 'AUCTION' }
      });

      // Submit the form
      fireEvent.click(screen.getByText('Save'));
    });

    // Verify the API was called with all updates
    await waitFor(() => {
      expect(items.update).toHaveBeenCalledWith('123', expect.objectContaining({
        name: 'Updated Item',
        custom_fields: expect.objectContaining({
          ebay: expect.objectContaining({
            listing_format: 'AUCTION'
          })
        })
      }));
    });
  });
});