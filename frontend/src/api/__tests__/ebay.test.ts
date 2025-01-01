import { ebay } from '../ebay';
import { apiClient } from '../client';
import type { EbayFields, EbayCategoryResponse, EbayExportResponse } from '../ebay';

jest.mock('../client', () => ({
  apiClient: {
    get: jest.fn(),
    post: jest.fn(),
  },
}));

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

  describe('exportItems', () => {
    const mockRequest = {
      item_ids: ['1', '2'],
      default_fields: {
        condition: 'NEW',
        listing_format: 'FIXED_PRICE',
      },
    };

    const mockResponse: EbayExportResponse = {
      success: true,
      message: 'Export successful',
      items_processed: 2,
      file_url: 'http://example.com/export.csv',
    };

    it('calls the correct endpoint with request data', async () => {
      (apiClient.post as jest.Mock).mockResolvedValue({ data: mockResponse });

      const result = await ebay.exportItems(mockRequest);

      expect(apiClient.post).toHaveBeenCalledWith('/api/ebay/export', mockRequest);
      expect(result).toEqual(mockResponse);
    });

    it('handles export errors correctly', async () => {
      const errorResponse: EbayExportResponse = {
        success: false,
        message: 'Export failed',
        items_processed: 0,
        errors: ['Invalid item data'],
      };

      (apiClient.post as jest.Mock).mockResolvedValue({ data: errorResponse });

      const result = await ebay.exportItems(mockRequest);

      expect(result.success).toBe(false);
      expect(result.errors).toContain('Invalid item data');
    });
  });
});