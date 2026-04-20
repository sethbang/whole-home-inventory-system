import { ebay } from '../ebay';
import { apiClient } from '../http';
import type { EbayFields, EbayCategoryResponse } from '../ebay';

jest.mock('../http', () => ({
  apiClient: {
    get: jest.fn(),
    post: jest.fn(),
  },
}));

// Stub URL + anchor APIs so the download helper can run in jsdom.
beforeAll(() => {
  (global.URL.createObjectURL as unknown) = jest.fn(() => 'blob:stub');
  (global.URL.revokeObjectURL as unknown) = jest.fn();
});

describe('ebay API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('getCategories', () => {
    const mockCategoryResponse: EbayCategoryResponse = {
      categories: [
        {
          id: '1',
          name: 'Electronics',
          subcategories: [
            { id: '1-1', name: 'Computers' }
          ]
        }
      ],
      suggested_category: { id: '1', name: 'Electronics' }
    };

    it('calls the correct endpoint without item ID', async () => {
      (apiClient.get as jest.Mock).mockResolvedValue({ data: mockCategoryResponse });

      const result = await ebay.getCategories();

      expect(apiClient.get).toHaveBeenCalledWith('/api/ebay/categories', { params: undefined });
      expect(result).toEqual(mockCategoryResponse);
    });

    it('includes item ID in params when provided', async () => {
      (apiClient.get as jest.Mock).mockResolvedValue({ data: mockCategoryResponse });

      const result = await ebay.getCategories('test-id');

      expect(apiClient.get).toHaveBeenCalledWith('/api/ebay/categories', {
        params: { item_id: 'test-id' }
      });
      expect(result).toEqual(mockCategoryResponse);
    });
  });

  describe('updateFields', () => {
    const mockFields: EbayFields = {
      condition: 'NEW',
      listing_format: 'FIXED_PRICE',
      duration: 'DAYS_7',
      shipping_service: 'USPS_PRIORITY',
    };

    it('calls the correct endpoint with data', async () => {
      (apiClient.post as jest.Mock).mockResolvedValue({ data: mockFields });

      const result = await ebay.updateFields('test-id', mockFields);

      expect(apiClient.post).toHaveBeenCalledWith(
        '/api/ebay/items/test-id/ebay-fields',
        mockFields
      );
      expect(result).toEqual(mockFields);
    });

    it('handles errors correctly', async () => {
      const error = new Error('API Error');
      (apiClient.post as jest.Mock).mockRejectedValue(error);

      await expect(ebay.updateFields('test-id', mockFields)).rejects.toThrow('API Error');
    });
  });

  describe('exportItems (streams CSV via blob download)', () => {
    const mockRequest = {
      item_ids: ['1', '2'],
      default_fields: {
        condition: 'NEW',
        listing_format: 'FIXED_PRICE',
      },
    };

    it('POSTs with blob responseType and triggers a download', async () => {
      const blob = new Blob(['id,title\n1,Drill'], { type: 'text/csv' });
      (apiClient.post as jest.Mock).mockResolvedValue({
        data: blob,
        headers: {
          'content-disposition': 'attachment; filename="whis-ebay-export.csv"',
        },
      });

      await ebay.exportItems(mockRequest);

      expect(apiClient.post).toHaveBeenCalledWith(
        '/api/ebay/export',
        mockRequest,
        expect.objectContaining({ responseType: 'blob' }),
      );
      // URL.createObjectURL is called on the blob to build the download link.
      expect(global.URL.createObjectURL).toHaveBeenCalled();
    });
  });
});