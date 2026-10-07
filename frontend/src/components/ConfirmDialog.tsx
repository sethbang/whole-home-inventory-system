/**
 * Accessible confirmation modal.
 *
 * Extracted from Dashboard's two near-identical inline delete dialogs.
 * Provides the a11y plumbing every modal needs but is easy to forget:
 *
 *  - ``role="dialog"`` + ``aria-modal="true"`` + ``aria-labelledby``
 *  - moves focus into the dialog on open, restores it to the previously
 *    focused element (the trigger) on close
 *  - a minimal Tab focus-trap so keyboard users can't escape the modal
 *  - ``Escape`` closes
 *
 * No new dependency — this is a hand-rolled trap, deliberately small.
 */

import React from 'react';
import { TrashIcon } from '@heroicons/react/24/outline';

export interface ConfirmDialogProps {
  /** Heading text — also wired up as ``aria-labelledby``. */
  title: string;
  /** Body copy. */
  message: React.ReactNode;
  /** Label for the confirm (destructive) button. */
  confirmLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
}

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';

export default function ConfirmDialog({
  title,
  message,
  confirmLabel,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const dialogRef = React.useRef<HTMLDivElement>(null);
  const titleId = React.useId();

  React.useEffect(() => {
    const previouslyFocused = document.activeElement as HTMLElement | null;
    // Move focus into the dialog once mounted.
    dialogRef.current?.focus();

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onCancel();
        return;
      }
      if (e.key !== 'Tab') return;
      const root = dialogRef.current;
      if (!root) return;
      const focusable = Array.from(
        root.querySelectorAll<HTMLElement>(FOCUSABLE),
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement;
      if (e.shiftKey && (active === first || active === root)) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && active === last) {
        e.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      // Restore focus to whatever triggered the dialog.
      previouslyFocused?.focus?.();
    };
  }, [onCancel]);

  return (
    <div className="fixed inset-0 bg-subtle bg-opacity-75 transition-opacity">
      <div className="fixed inset-0 z-10 overflow-y-auto">
        <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
          <div
            ref={dialogRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            tabIndex={-1}
            className="relative transform overflow-hidden rounded-lg bg-surface-raised px-4 pb-4 pt-5 text-left shadow-xl transition-all focus:outline-none sm:my-8 sm:w-full sm:max-w-lg sm:p-6"
          >
            <div className="sm:flex sm:items-start">
              <div className="mx-auto flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-danger-subtle sm:mx-0 sm:h-10 sm:w-10">
                <TrashIcon className="h-6 w-6 text-danger" aria-hidden="true" />
              </div>
              <div className="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left">
                <h3
                  id={titleId}
                  className="text-base font-semibold leading-6 text-fg"
                >
                  {title}
                </h3>
                <div className="mt-2">
                  <p className="text-sm text-subtle">{message}</p>
                </div>
              </div>
            </div>
            <div className="mt-5 sm:mt-4 sm:flex sm:flex-row-reverse">
              <button
                type="button"
                className="inline-flex w-full justify-center rounded-md bg-danger px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-danger sm:ml-3 sm:w-auto"
                onClick={onConfirm}
              >
                {confirmLabel}
              </button>
              <button
                type="button"
                className="mt-3 inline-flex w-full justify-center rounded-md bg-surface-raised px-3 py-2 text-sm font-semibold text-fg shadow-sm ring-1 ring-inset ring-line hover:bg-surface-muted sm:mt-0 sm:w-auto"
                onClick={onCancel}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
