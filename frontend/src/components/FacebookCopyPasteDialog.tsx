/**
 * Modal shown when the user clicks "Copy-paste block" on an item's
 * Facebook tab. Fetches the server-rendered block, displays it in a
 * read-only textarea, and offers two actions:
 *
 * - "Copy to clipboard"  — uses navigator.clipboard.writeText with a
 *   document.execCommand fallback for browsers that refuse the
 *   permission in non-secure contexts.
 * - "Download images ZIP" — kicks off the GET /api/facebook/items/{id}/
 *   images.zip flow via the download helper.
 *
 * The dialog handles its own loading and error states so the caller
 * just needs to pass the item id and an ``onClose`` callback.
 */

import { useEffect, useRef, useState } from 'react';

import { facebook } from '../api/facebook';
import { apiErrorMessage } from '../api/errors';
import { logger } from '../lib/logger';
import type { FbCopyPasteBlock } from '../api/types';

interface FacebookCopyPasteDialogProps {
  itemId: string;
  onClose: () => void;
}

export default function FacebookCopyPasteDialog({
  itemId,
  onClose,
}: FacebookCopyPasteDialogProps) {
  const [block, setBlock] = useState<FbCopyPasteBlock | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    facebook
      .copyPasteBlock(itemId)
      .then((b) => {
        if (!cancelled) setBlock(b);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(apiErrorMessage(err, 'Failed to generate copy-paste block'));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [itemId]);

  const handleCopy = async () => {
    if (!block) return;
    try {
      if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
        await navigator.clipboard.writeText(block.block);
      } else if (textareaRef.current) {
        textareaRef.current.select();
        document.execCommand('copy');
      }
      setStatus('Copied to clipboard.');
    } catch (err) {
      logger.error('clipboard write failed', err);
      setError('Copy failed — select the text manually.');
    }
  };

  const handleDownloadImages = async () => {
    setError(null);
    setDownloading(true);
    try {
      await facebook.downloadImagesZip(itemId);
      setStatus('Images downloaded.');
    } catch (err) {
      setError(apiErrorMessage(err, 'Failed to download images'));
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="fb-cp-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
    >
      <div className="w-full max-w-2xl rounded-lg bg-white p-6 shadow-xl">
        <div className="flex items-start justify-between">
          <h2 id="fb-cp-title" className="text-lg font-semibold text-gray-900">
            Facebook Marketplace copy-paste block
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700"
            aria-label="Close"
          >
            ✕
          </button>
        </div>
        <p className="mt-1 text-xs text-gray-600">
          Paste this into the FB Marketplace listing form. Images are a
          separate download — Facebook doesn't let the browser drag URLs in.
        </p>

        {error && (
          <div role="alert" className="mt-3 rounded-md bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}
        {status && (
          <div className="mt-3 rounded-md bg-green-50 p-3 text-sm text-green-700">
            {status}
          </div>
        )}

        {!block && !error && (
          <div className="mt-4 text-sm text-gray-500">Generating block…</div>
        )}

        {block && (
          <>
            <textarea
              ref={textareaRef}
              readOnly
              value={block.block}
              rows={12}
              aria-label="Copy-paste block"
              className="mt-4 block w-full rounded-md border-gray-300 font-mono text-sm shadow-sm"
            />
            {block.price !== undefined && block.price !== null && (
              <p className="mt-2 text-xs text-gray-600">
                Price: ${block.price.toFixed(2)}
                {block.suggested_category
                  ? ` · Suggested category: ${block.suggested_category}`
                  : ''}
              </p>
            )}
          </>
        )}

        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            onClick={handleDownloadImages}
            disabled={downloading}
            className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-60"
          >
            {downloading ? 'Downloading…' : 'Download images ZIP'}
          </button>
          <button
            type="button"
            onClick={handleCopy}
            disabled={!block}
            className="rounded-md border border-transparent bg-primary px-3 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-primary-hover disabled:opacity-60"
          >
            Copy to clipboard
          </button>
        </div>
      </div>
    </div>
  );
}
