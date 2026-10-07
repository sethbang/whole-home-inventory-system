import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

import ImageGallery from '../ImageGallery';
import type { ItemImage } from '../../api/client';

function makeImage(overrides: Partial<ItemImage> = {}): ItemImage {
  return {
    id: 'img-1',
    item_id: 'item-1',
    filename: 'photo.jpg',
    file_path: 'uploads/photo.jpg',
    thumbnail_path: 'uploads/thumb_photo.webp',
    uploaded_at: '2026-05-04T00:00:00Z',
    ...overrides,
  } as ItemImage;
}

describe('ImageGallery', () => {
  it('renders thumbnail src as an absolute path so vite proxies /uploads', () => {
    // Regression: stored paths are relative ("uploads/<file>") and a
    // page at /items/<id> would otherwise resolve them to
    // /items/uploads/... — falling through to the SPA catch-all.
    render(<ImageGallery images={[makeImage()]} />);
    const img = screen.getByAltText('photo.jpg');
    expect(img).toHaveAttribute('src', '/uploads/thumb_photo.webp');
  });

  it('falls back to file_path when thumbnail_path is missing', () => {
    render(
      <ImageGallery images={[makeImage({ thumbnail_path: null })]} />,
    );
    expect(screen.getByAltText('photo.jpg')).toHaveAttribute(
      'src',
      '/uploads/photo.jpg',
    );
  });

  it('passes through already-absolute URLs untouched', () => {
    render(
      <ImageGallery
        images={[
          makeImage({
            thumbnail_path: 'https://cdn.example/thumb.webp',
          }),
        ]}
      />,
    );
    expect(screen.getByAltText('photo.jpg')).toHaveAttribute(
      'src',
      'https://cdn.example/thumb.webp',
    );
  });

  it('renders delete button with type="button" so it does not submit a parent <form>', () => {
    // Regression: ImageGallery is rendered inside ItemDetail's edit form.
    // A default-typed button submits the form on click, triggering
    // updateItemMutation → navigate('/') and bouncing the user out.
    const onDelete = vi.fn();
    render(
      <ImageGallery images={[makeImage()]} onDelete={onDelete} />,
    );
    const deleteButton = screen.getByRole('button', { name: 'Delete image' });
    expect(deleteButton).toHaveAttribute('type', 'button');
  });

  it('invokes onDelete with the image id when the delete button is clicked', () => {
    const onDelete = vi.fn();
    render(
      <ImageGallery images={[makeImage()]} onDelete={onDelete} />,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Delete image' }));
    expect(onDelete).toHaveBeenCalledWith('img-1');
  });

  it('omits the delete button when no onDelete handler is provided', () => {
    render(<ImageGallery images={[makeImage()]} />);
    expect(
      screen.queryByRole('button', { name: 'Delete image' }),
    ).toBeNull();
  });

  it('opens a full-resolution preview when the thumbnail is clicked', () => {
    // The lightbox uses the original `file_path` (not thumbnail_path) so
    // the user sees the full uncropped photo.
    render(<ImageGallery images={[makeImage()]} />);
    expect(screen.queryByRole('dialog')).toBeNull();

    fireEvent.click(screen.getByAltText('photo.jpg'));

    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    // Two images now: the gallery thumbnail and the lightbox original.
    const fullSize = screen.getAllByAltText('photo.jpg').find((img) =>
      img.getAttribute('src') === '/uploads/photo.jpg',
    );
    expect(fullSize).toBeDefined();
  });

  it('closes the preview when the backdrop is clicked', () => {
    render(<ImageGallery images={[makeImage()]} />);
    fireEvent.click(screen.getByAltText('photo.jpg'));
    expect(screen.getByRole('dialog')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('dialog'));
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('keeps the preview open when the lightbox image itself is clicked', () => {
    // stopPropagation on the lightbox <img> prevents accidental dismissal
    // when the user clicks on the photo to focus or pan.
    render(<ImageGallery images={[makeImage()]} />);
    fireEvent.click(screen.getByAltText('photo.jpg'));

    const fullSize = screen.getAllByAltText('photo.jpg').find((img) =>
      img.getAttribute('src') === '/uploads/photo.jpg',
    );
    expect(fullSize).toBeDefined();
    fireEvent.click(fullSize!);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('closes the preview when Escape is pressed', () => {
    render(<ImageGallery images={[makeImage()]} />);
    fireEvent.click(screen.getByAltText('photo.jpg'));
    expect(screen.getByRole('dialog')).toBeInTheDocument();

    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('closes the preview when the explicit close button is clicked', () => {
    render(<ImageGallery images={[makeImage()]} />);
    fireEvent.click(screen.getByAltText('photo.jpg'));

    fireEvent.click(screen.getByRole('button', { name: 'Close preview' }));
    expect(screen.queryByRole('dialog')).toBeNull();
  });
});
