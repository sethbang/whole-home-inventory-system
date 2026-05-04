import { backups } from '../backups';
import { apiClient } from '../http';

vi.mock('../http', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

beforeAll(() => {
  (globalThis.URL.createObjectURL as unknown) = vi.fn(() => 'blob:stub');
  (globalThis.URL.revokeObjectURL as unknown) = vi.fn();
});

beforeEach(() => {
  vi.clearAllMocks();
});

describe('backups.download', () => {
  it('GETs through the authenticated axios client with blob responseType', async () => {
    // Regression: previously used window.open, which navigates without the
    // Authorization header and so always 401'd against the protected route.
    const blob = new Blob(['zipdata'], { type: 'application/zip' });
    (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: blob,
      headers: {
        'content-disposition': 'attachment; filename="whis-backup.zip"',
      },
    });

    await backups.download('backup-1');

    expect(apiClient.get).toHaveBeenCalledWith(
      '/api/backups/backup-1/download',
      expect.objectContaining({ responseType: 'blob' }),
    );
    expect(globalThis.URL.createObjectURL).toHaveBeenCalled();
  });

  it('propagates errors from the api client', async () => {
    const err = new Error('boom');
    (apiClient.get as ReturnType<typeof vi.fn>).mockRejectedValue(err);

    await expect(backups.download('backup-1')).rejects.toThrow('boom');
  });
});
