import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';

import ItemCard from '../ItemCard';
import type { Item, ItemImage } from '../../api/types';

function makeItem(overrides: Partial<Item> = {}): Item {
  return {
    id: 'item-1',
    owner_id: 'owner-1',
    name: 'Cordless Drill',
    category: 'Tools',
    location: 'Garage',
    current_value: 79.5,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    images: [],
    ...overrides,
  } as Item;
}

function makeImage(overrides: Partial<ItemImage> = {}): ItemImage {
  return {
    id: 'img-1',
    item_id: 'item-1',
    filename: 'drill.jpg',
    file_path: 'uploads/drill.jpg',
    thumbnail_path: 'uploads/thumb_drill.webp',
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  } as ItemImage;
}

function renderCard(props: Parameters<typeof ItemCard>[0]) {
  return render(
    <MemoryRouter>
      <ItemCard {...props} />
    </MemoryRouter>,
  );
}

describe('ItemCard', () => {
  it('renders the placeholder when there are no images', () => {
    const { container } = renderCard({ item: makeItem({ images: [] }) });
    expect(screen.getByTestId('item-card-placeholder')).toBeInTheDocument();
    expect(container.querySelector('img')).toBeNull();
  });

  it('renders the thumbnail with an absolute /uploads URL', () => {
    const { container } = renderCard({
      item: makeItem({ images: [makeImage()] }),
    });
    const img = container.querySelector('img');
    expect(img).not.toBeNull();
    expect(img).toHaveAttribute('src', '/uploads/thumb_drill.webp');
  });

  it('falls back to file_path when thumbnail_path is missing', () => {
    const { container } = renderCard({
      item: makeItem({
        images: [makeImage({ thumbnail_path: null })],
      }),
    });
    expect(container.querySelector('img')).toHaveAttribute(
      'src',
      '/uploads/drill.jpg',
    );
  });

  it('formats current_value as USD and renders a dash when null', () => {
    const { rerender } = renderCard({ item: makeItem({ current_value: 1234.5 }) });
    expect(screen.getByText('$1234.50')).toBeInTheDocument();

    rerender(
      <MemoryRouter>
        <ItemCard item={makeItem({ current_value: null })} />
      </MemoryRouter>,
    );
    expect(screen.getByText('—')).toBeInTheDocument();
  });

  it('links to the item detail page', () => {
    renderCard({ item: makeItem({ id: 'abc-123' }) });
    expect(screen.getByRole('link')).toHaveAttribute('href', '/items/abc-123');
  });

  it('renders the row layout when layout="row" is passed', () => {
    renderCard({
      item: makeItem({ images: [makeImage()] }),
      layout: 'row',
    });
    // Row layout puts category alongside location with a separator.
    expect(screen.getByText(/Garage · Tools/)).toBeInTheDocument();
  });
});
