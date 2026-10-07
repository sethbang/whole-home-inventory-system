import { useEffect, useState } from 'react';
import { ItemImage } from '../api/client';

export interface ImageGalleryProps {
  images: ItemImage[];
  onDelete?: (imageId: string) => void;
}

// Image rows store file_path / thumbnail_path as "uploads/<filename>" — the
// joined model column. The browser needs an absolute path so vite's proxy
// matches `/uploads`; otherwise a relative ref from `/items/<id>` resolves
// to `/items/uploads/...` which falls through to the SPA catch-all and the
// <img> renders broken (no request ever reaches the backend).
function toAbsoluteUrl(path: string | null | undefined): string {
  if (!path) return '';
  if (path.startsWith('/') || /^https?:\/\//.test(path)) return path;
  return `/${path}`;
}

export default function ImageGallery({ images, onDelete }: ImageGalleryProps) {
  const [previewImage, setPreviewImage] = useState<ItemImage | null>(null);

  // Close the lightbox on Escape. Bound only while a preview is active so
  // we don't burn a global key listener for every gallery on the page.
  useEffect(() => {
    if (!previewImage) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setPreviewImage(null);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [previewImage]);

  const handleDelete = (imageId: string) => {
    if (onDelete) {
      onDelete(imageId);
    }
  };

  const openPreview = (image: ItemImage) => setPreviewImage(image);

  return (
    <>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        {images.map((image) => (
          <div key={image.id} className="relative group aspect-square">
            {/*
              Square cell prevents the wide-rectangle double-crop the gallery
              had before — the backend already produces a 512×512 thumbnail
              via `ImageOps.fit`, so a 1:1 cell shows the thumbnail's full
              content rather than re-cropping the top/bottom away. Click
              the image to open the lightbox showing the original
              full-resolution upload.
            */}
            <img
              src={toAbsoluteUrl(image.thumbnail_path ?? image.file_path)}
              alt={image.filename}
              loading="lazy"
              role="button"
              tabIndex={0}
              onClick={() => openPreview(image)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  openPreview(image);
                }
              }}
              className="block h-full w-full object-cover rounded-lg cursor-zoom-in focus:outline-none focus:ring-2 focus:ring-primary"
            />
            {/*
              Tailwind v4 dropped the `bg-opacity-*` utilities; the v3-syntax
              `bg-opacity-0` silently degrades to fully-opaque `bg-overlay`,
              which used to mask the underlying image as a solid black square.
              v4-native syntax `bg-overlay/0` + `group-hover:bg-overlay/30` keeps
              the overlay transparent until hover, with a dimmer veil so the
              delete button stays readable without obscuring the photo.
              `pointer-events-none` lets clicks fall through to the <img>;
              the delete button re-enables them locally.
            */}
            <div className="pointer-events-none absolute inset-0 bg-overlay/0 group-hover:bg-overlay/30 transition-colors rounded-lg flex items-end justify-end p-2">
              {onDelete && (
                <button
                  // type="button" is load-bearing: ImageGallery is rendered
                  // inside the ItemDetail edit <form>, so without this the
                  // default `submit` type fires the surrounding form, which
                  // triggers updateItemMutation → navigate('/') and bounces
                  // the user back to the dashboard.
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(image.id);
                  }}
                  className="pointer-events-auto opacity-0 group-hover:opacity-100 transition-opacity p-2 bg-danger text-white rounded-full hover:bg-danger focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-danger"
                  aria-label="Delete image"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {previewImage && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={`${previewImage.filename} preview`}
          className="fixed inset-0 z-50 flex items-center justify-center bg-overlay/80 p-4"
          onClick={() => setPreviewImage(null)}
        >
          <button
            type="button"
            aria-label="Close preview"
            onClick={() => setPreviewImage(null)}
            className="absolute top-4 right-4 text-white text-3xl leading-none rounded-full bg-overlay/40 hover:bg-overlay/60 w-10 h-10 flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-white"
          >
            ✕
          </button>
          {/*
            Original full-resolution upload, not the thumbnail. `object-contain`
            + max-h/w ensures the whole photo fits inside the viewport with
            no further cropping. stopPropagation on the image itself keeps
            click-on-image from also closing the lightbox.
          */}
          <img
            src={toAbsoluteUrl(previewImage.file_path)}
            alt={previewImage.filename}
            onClick={(e) => e.stopPropagation()}
            className="max-h-full max-w-full object-contain rounded-md shadow-2xl"
          />
        </div>
      )}
    </>
  );
}
