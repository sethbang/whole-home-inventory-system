import { facebook } from '../facebook';
import { apiClient } from '../http';

jest.mock('../http', () => ({
  apiClient: {
    get: jest.fn(),
    post: jest.fn(),
  },
}));

beforeAll(() => {
  (global.URL.createObjectURL as unknown) = jest.fn(() => 'blob:stub');
  (global.URL.revokeObjectURL as unknown) = jest.fn();
});

beforeEach(() => {
  jest.clearAllMocks();
});

describe('facebook API client', () => {
  it('getCategories hits /api/facebook/categories', async () => {
    (apiClient.get as jest.Mock).mockResolvedValue({
      data: { categories: ['Tools', 'Miscellaneous'] },
    });
    const result = await facebook.getCategories();
    expect(apiClient.get).toHaveBeenCalledWith('/api/facebook/categories');
    expect(result.categories).toContain('Tools');
  });

  it('updateFields posts FbFields to the per-item endpoint', async () => {
    (apiClient.post as jest.Mock).mockResolvedValue({
      data: { price: 49.99, condition: 'USED_LIKE_NEW' },
    });
    const result = await facebook.updateFields('abc', {
      price: 49.99,
      condition: 'USED_LIKE_NEW',
    });
    expect(apiClient.post).toHaveBeenCalledWith(
      '/api/facebook/items/abc/fb-fields',
      { price: 49.99, condition: 'USED_LIKE_NEW' },
    );
    expect(result.price).toBe(49.99);
  });

  it('copyPasteBlock posts to the copy-paste endpoint', async () => {
    (apiClient.post as jest.Mock).mockResolvedValue({
      data: {
        title: 'Drill',
        description: 'great drill',
        price: 60,
        suggested_category: 'Tools',
        tags: ['Tools'],
        block: 'Drill\nPrice: $60.00\nCategory: Tools',
      },
    });
    const result = await facebook.copyPasteBlock('abc');
    expect(apiClient.post).toHaveBeenCalledWith(
      '/api/facebook/items/abc/copy-paste',
    );
    expect(result.title).toBe('Drill');
  });

  it('downloadImagesZip triggers a blob GET', async () => {
    (apiClient.get as jest.Mock).mockResolvedValue({
      data: new Blob(['zipbytes']),
      headers: {
        'content-disposition': 'attachment; filename="item-abc-images.zip"',
      },
    });
    await facebook.downloadImagesZip('abc');
    expect(apiClient.get).toHaveBeenCalledWith(
      '/api/facebook/items/abc/images.zip',
      expect.objectContaining({ responseType: 'blob' }),
    );
  });

  it('exportItems triggers a blob POST', async () => {
    (apiClient.post as jest.Mock).mockResolvedValue({
      data: new Blob(['csvbytes']),
      headers: {
        'content-disposition': 'attachment; filename="whis-facebook-catalog.csv"',
      },
    });
    await facebook.exportItems({ item_ids: ['a', 'b'] });
    expect(apiClient.post).toHaveBeenCalledWith(
      '/api/facebook/export',
      { item_ids: ['a', 'b'] },
      expect.objectContaining({ responseType: 'blob' }),
    );
  });
});
