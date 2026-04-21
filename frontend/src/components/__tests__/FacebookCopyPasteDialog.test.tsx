import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

import FacebookCopyPasteDialog from '../FacebookCopyPasteDialog';
import { facebook } from '../../api/facebook';
import { ApiError } from '../../api/errors';

jest.mock('../../api/facebook', () => ({
  facebook: {
    copyPasteBlock: jest.fn(),
    downloadImagesZip: jest.fn(),
  },
}));

const clipboardWrite = jest.fn().mockResolvedValue(undefined);

beforeAll(() => {
  Object.defineProperty(global.navigator, 'clipboard', {
    value: { writeText: clipboardWrite },
    configurable: true,
  });
});

beforeEach(() => {
  jest.clearAllMocks();
  clipboardWrite.mockClear();
});

describe('FacebookCopyPasteDialog', () => {
  it('fetches and renders the copy-paste block', async () => {
    (facebook.copyPasteBlock as jest.Mock).mockResolvedValue({
      title: 'Drill',
      description: 'great',
      price: 60,
      suggested_category: 'Tools',
      tags: ['Tools'],
      block: 'Drill\nPrice: $60.00',
    });

    render(<FacebookCopyPasteDialog itemId="abc" onClose={() => {}} />);
    expect(screen.getByText(/generating block/i)).toBeInTheDocument();

    const textarea = await screen.findByLabelText('Copy-paste block');
    expect(textarea).toHaveValue('Drill\nPrice: $60.00');
    expect(facebook.copyPasteBlock).toHaveBeenCalledWith('abc');
    // The "Price: $60.00" caption appears below the textarea; assert at
    // least one match (the textarea itself also contains the string).
    expect(screen.getAllByText(/price: \$60.00/i).length).toBeGreaterThan(0);
  });

  it('copies the block to the clipboard on button click', async () => {
    (facebook.copyPasteBlock as jest.Mock).mockResolvedValue({
      title: 'Drill',
      description: '',
      price: null,
      tags: [],
      block: 'just the title',
    });

    render(<FacebookCopyPasteDialog itemId="abc" onClose={() => {}} />);
    await screen.findByLabelText('Copy-paste block');

    fireEvent.click(screen.getByRole('button', { name: /copy to clipboard/i }));

    await waitFor(() => {
      expect(clipboardWrite).toHaveBeenCalledWith('just the title');
    });
    expect(await screen.findByText(/copied to clipboard/i)).toBeInTheDocument();
  });

  it('triggers the image-zip download when the button is clicked', async () => {
    (facebook.copyPasteBlock as jest.Mock).mockResolvedValue({
      title: 'Drill',
      description: '',
      price: null,
      tags: [],
      block: 'Drill',
    });
    (facebook.downloadImagesZip as jest.Mock).mockResolvedValue(undefined);

    render(<FacebookCopyPasteDialog itemId="abc" onClose={() => {}} />);
    await screen.findByLabelText('Copy-paste block');

    fireEvent.click(
      screen.getByRole('button', { name: /download images zip/i }),
    );

    await waitFor(() =>
      expect(facebook.downloadImagesZip).toHaveBeenCalledWith('abc'),
    );
    expect(await screen.findByText(/images downloaded/i)).toBeInTheDocument();
  });

  it('surfaces ApiError.detail when the block fetch fails', async () => {
    (facebook.copyPasteBlock as jest.Mock).mockRejectedValue(
      new ApiError(500, 'server unavailable'),
    );

    render(<FacebookCopyPasteDialog itemId="abc" onClose={() => {}} />);

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/server unavailable/i);
  });

  it('calls onClose when the close button is clicked', async () => {
    (facebook.copyPasteBlock as jest.Mock).mockResolvedValue({
      title: 'Drill',
      description: '',
      price: null,
      tags: [],
      block: 'Drill',
    });
    const onClose = jest.fn();

    render(<FacebookCopyPasteDialog itemId="abc" onClose={onClose} />);
    await screen.findByLabelText('Copy-paste block');

    fireEvent.click(screen.getByRole('button', { name: /close/i }));
    expect(onClose).toHaveBeenCalled();
  });
});
