/**
 * Helper for server endpoints that stream a binary blob in response to a
 * POST (bulk exports, image zips, etc.). Can't use ``window.open`` because
 * the endpoint wants a request body, so we use axios with
 * ``responseType: 'blob'`` and trigger a browser download via a hidden
 * anchor element.
 *
 * Filename resolution order: explicit ``filename`` argument, then the
 * server's Content-Disposition header, then the fallback.
 */

import { apiClient } from './http';

interface DownloadOptions {
  /** Override the saved filename. If unset, parsed from Content-Disposition. */
  filename?: string;
  /** Fallback if neither ``filename`` nor Content-Disposition gives one. */
  fallback?: string;
}

const CONTENT_DISPOSITION_FILENAME = /filename="?([^";]+)"?/i;

export async function downloadPost(
  url: string,
  body: unknown,
  opts: DownloadOptions = {},
): Promise<void> {
  const response = await apiClient.post(url, body, {
    responseType: 'blob',
  });

  let filename = opts.filename;
  if (!filename) {
    const cd =
      (response.headers as Record<string, string>)['content-disposition'] ?? '';
    const match = CONTENT_DISPOSITION_FILENAME.exec(cd);
    if (match) filename = match[1];
  }
  filename = filename ?? opts.fallback ?? 'download';

  const blobUrl = URL.createObjectURL(response.data as Blob);
  const anchor = document.createElement('a');
  anchor.href = blobUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(blobUrl);
}

export async function downloadGet(
  url: string,
  opts: DownloadOptions = {},
): Promise<void> {
  const response = await apiClient.get(url, { responseType: 'blob' });

  let filename = opts.filename;
  if (!filename) {
    const cd =
      (response.headers as Record<string, string>)['content-disposition'] ?? '';
    const match = CONTENT_DISPOSITION_FILENAME.exec(cd);
    if (match) filename = match[1];
  }
  filename = filename ?? opts.fallback ?? 'download';

  const blobUrl = URL.createObjectURL(response.data as Blob);
  const anchor = document.createElement('a');
  anchor.href = blobUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(blobUrl);
}
