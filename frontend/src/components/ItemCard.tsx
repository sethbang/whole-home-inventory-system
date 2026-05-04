import { Link } from 'react-router-dom';
import type { Item, ItemImage } from '../api/types';

export type ItemCardLayout = 'card' | 'row';

export interface ItemCardProps {
  item: Item;
  layout?: ItemCardLayout;
}

function toAbsoluteUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  if (path.startsWith('/') || /^https?:\/\//.test(path)) return path;
  return `/${path}`;
}

function pickThumbnail(images: ItemImage[] | undefined): string | null {
  const first = images?.[0];
  if (!first) return null;
  return (
    toAbsoluteUrl(first.thumbnail_path) ??
    toAbsoluteUrl(first.file_path) ??
    toAbsoluteUrl(first.filename ? `uploads/${first.filename}` : null)
  );
}

function formatValue(v: number | null | undefined): string {
  if (v === null || v === undefined) return '—';
  return `$${v.toFixed(2)}`;
}

function ImagePlaceholder({ className }: { className: string }) {
  return (
    <div
      className={`${className} flex items-center justify-center bg-primary-subtle text-primary-hover`}
      aria-hidden="true"
      data-testid="item-card-placeholder"
    >
      <svg
        className="h-1/3 w-1/3 opacity-60"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={1.5}
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"
        />
      </svg>
    </div>
  );
}

export default function ItemCard({ item, layout = 'card' }: ItemCardProps) {
  const thumb = pickThumbnail(item.images);
  const detailUrl = `/items/${item.id}`;

  if (layout === 'row') {
    return (
      <Link
        to={detailUrl}
        className="flex items-center gap-4 rounded-lg border border-gray-200 bg-white p-3 hover:bg-primary-subtle focus:outline-none focus:ring-2 focus:ring-primary"
      >
        {thumb ? (
          <img
            src={thumb}
            alt=""
            className="h-16 w-16 flex-shrink-0 rounded-md object-cover"
            loading="lazy"
          />
        ) : (
          <ImagePlaceholder className="h-16 w-16 flex-shrink-0 rounded-md" />
        )}
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-medium text-gray-900">
            {item.name}
          </div>
          <div className="mt-0.5 truncate text-xs text-gray-500">
            {item.location}
            {item.category ? ` · ${item.category}` : ''}
          </div>
        </div>
        <div className="ml-auto text-sm font-medium text-gray-900">
          {formatValue(item.current_value)}
        </div>
      </Link>
    );
  }

  return (
    <Link
      to={detailUrl}
      className="group flex flex-col overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm transition hover:border-primary hover:shadow focus:outline-none focus:ring-2 focus:ring-primary"
    >
      {thumb ? (
        <img
          src={thumb}
          alt=""
          className="aspect-[4/3] w-full object-cover"
          loading="lazy"
        />
      ) : (
        <ImagePlaceholder className="aspect-[4/3] w-full" />
      )}
      <div className="flex flex-1 flex-col p-3">
        <h3 className="truncate text-sm font-medium text-gray-900 group-hover:text-primary-hover">
          {item.name}
        </h3>
        <div className="mt-1 flex items-center gap-1.5 text-xs text-gray-500">
          <span className="truncate">{item.location || '—'}</span>
          {item.category && (
            <span className="inline-flex shrink-0 items-center rounded bg-primary-subtle px-1.5 py-0.5 text-[11px] font-medium text-primary-hover">
              {item.category}
            </span>
          )}
        </div>
        <div className="mt-3 text-sm font-semibold text-gray-900">
          {formatValue(item.current_value)}
        </div>
      </div>
    </Link>
  );
}
