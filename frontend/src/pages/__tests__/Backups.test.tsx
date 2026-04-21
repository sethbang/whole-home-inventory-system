import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import Backups from '../Backups';
import { backups } from '../../api/backups';

vi.mock('../../api/backups', () => ({
  backups: {
    list: vi.fn(),
    create: vi.fn(),
    previewRestore: vi.fn(),
    commitRestore: vi.fn(),
    upload: vi.fn(),
    delete: vi.fn(),
    download: vi.fn(),
  },
}));

const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});

const mockBackup = {
  id: 'backup-1',
  owner_id: 'user-1',
  filename: 'backup.zip',
  file_path: '/backups/backup.zip',
  size_bytes: 1024,
  item_count: 3,
  image_count: 0,
  created_at: '2026-04-20T00:00:00Z',
  status: 'completed',
};

const renderBackups = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Backups />
      </MemoryRouter>
    </QueryClientProvider>,
  );
};

beforeEach(() => {
  vi.clearAllMocks();
  alertSpy.mockClear();
  (backups.list as ReturnType<typeof vi.fn>).mockResolvedValue({ backups: [mockBackup] });
});

describe('Backups two-phase restore', () => {
  it('shows the preview dialog after clicking Restore', async () => {
    (backups.previewRestore as ReturnType<typeof vi.fn>).mockResolvedValue({
      success: true,
      message: 'Dry run',
      dry_run: true,
      current_item_count: 5,
      backup_item_count: 3,
      backup_image_count: 2,
    });

    renderBackups();
    const restore = await screen.findByRole('button', { name: /^restore$/i });
    fireEvent.click(restore);

    await screen.findByRole('dialog');
    expect(backups.previewRestore).toHaveBeenCalledWith('backup-1');
    expect(screen.getByText(/delete 5 existing item/)).toBeInTheDocument();
    expect(screen.getByText(/3 item\(s\)/)).toBeInTheDocument();
    expect(screen.getByText(/2 image\(s\)/)).toBeInTheDocument();
  });

  it('rejects a wrong-count confirmation client-side', async () => {
    (backups.previewRestore as ReturnType<typeof vi.fn>).mockResolvedValue({
      success: true,
      message: 'Dry run',
      dry_run: true,
      current_item_count: 5,
      backup_item_count: 3,
      backup_image_count: 0,
    });

    renderBackups();
    fireEvent.click(await screen.findByRole('button', { name: /^restore$/i }));
    await screen.findByRole('dialog');

    fireEvent.change(screen.getByLabelText(/confirm item count/i), {
      target: { value: '3' }, // wrong — expected 5
    });
    // The first "Restore" button is the row action; the dialog's submit
    // button is the last one.
    const restoreButtons = screen.getAllByRole('button', { name: /^restore$/i });
    fireEvent.click(restoreButtons[restoreButtons.length - 1]);

    expect(await screen.findByText(/type 5 to confirm/i)).toBeInTheDocument();
    expect(backups.commitRestore).not.toHaveBeenCalled();
  });

  it('commits with the correct count and shows success', async () => {
    (backups.previewRestore as ReturnType<typeof vi.fn>).mockResolvedValue({
      success: true,
      message: 'Dry run',
      dry_run: true,
      current_item_count: 5,
      backup_item_count: 3,
      backup_image_count: 2,
    });
    (backups.commitRestore as ReturnType<typeof vi.fn>).mockResolvedValue({
      success: true,
      message: 'Restored',
      items_restored: 3,
      images_restored: 2,
    });

    renderBackups();
    fireEvent.click(await screen.findByRole('button', { name: /^restore$/i }));
    await screen.findByRole('dialog');

    fireEvent.change(screen.getByLabelText(/confirm item count/i), {
      target: { value: '5' },
    });
    fireEvent.click(
      screen.getAllByRole('button', { name: /^restore$/i }).pop()!,
    );

    await waitFor(() =>
      expect(backups.commitRestore).toHaveBeenCalledWith('backup-1', 5),
    );
    await waitFor(() => expect(alertSpy).toHaveBeenCalled());
  });
});
