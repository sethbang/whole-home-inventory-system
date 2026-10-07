import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

import { SectionErrorBoundary } from '../ErrorBoundary';
import { ApiError } from '../../api/errors';

// react-error-boundary logs the swallowed error to console.error by design;
// silence it so Jest output stays clean.
let consoleErrorSpy: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
});
afterEach(() => {
  consoleErrorSpy.mockRestore();
});

function Kaboom({ message = 'boom' }: { message?: string }): React.ReactElement {
  throw new Error(message);
}

function KaboomApi(): React.ReactElement {
  throw new ApiError(500, 'database exploded');
}

describe('SectionErrorBoundary', () => {
  it('renders children when they do not throw', () => {
    render(
      <SectionErrorBoundary label="widget">
        <p>hello world</p>
      </SectionErrorBoundary>,
    );
    expect(screen.getByText('hello world')).toBeInTheDocument();
  });

  it('renders the default fallback when a child throws', () => {
    render(
      <SectionErrorBoundary label="widget">
        <Kaboom />
      </SectionErrorBoundary>,
    );
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/widget failed to load/i)).toBeInTheDocument();
    expect(screen.getByText(/boom/i)).toBeInTheDocument();
  });

  it('surfaces ApiError.detail in the fallback', () => {
    render(
      <SectionErrorBoundary label="pricing card">
        <KaboomApi />
      </SectionErrorBoundary>,
    );
    expect(screen.getByText(/database exploded/i)).toBeInTheDocument();
  });

  it('resets when the user clicks Try again', () => {
    let shouldThrow = true;
    function MaybeBroken() {
      if (shouldThrow) {
        throw new Error('not yet');
      }
      return <p>fixed</p>;
    }

    const { rerender } = render(
      <SectionErrorBoundary label="widget">
        <MaybeBroken />
      </SectionErrorBoundary>,
    );
    expect(screen.getByRole('alert')).toBeInTheDocument();

    shouldThrow = false;
    fireEvent.click(screen.getByRole('button', { name: /try again/i }));

    // After the reset, render the boundary again so the child re-mounts.
    rerender(
      <SectionErrorBoundary label="widget">
        <MaybeBroken />
      </SectionErrorBoundary>,
    );
    expect(screen.getByText('fixed')).toBeInTheDocument();
  });

  it('resetKey change re-renders the children', () => {
    let shouldThrow = true;
    function MaybeBroken() {
      if (shouldThrow) throw new Error('still broken');
      return <p>recovered</p>;
    }

    const { rerender } = render(
      <SectionErrorBoundary label="widget" resetKey="v1">
        <MaybeBroken />
      </SectionErrorBoundary>,
    );
    expect(screen.getByRole('alert')).toBeInTheDocument();

    shouldThrow = false;
    rerender(
      <SectionErrorBoundary label="widget" resetKey="v2">
        <MaybeBroken />
      </SectionErrorBoundary>,
    );
    expect(screen.getByText('recovered')).toBeInTheDocument();
  });

  it('honors a custom fallback override', () => {
    render(
      <SectionErrorBoundary
        label="widget"
        fallback={({ error }) => (
          <div data-testid="custom-fallback">custom: {(error as Error).message}</div>
        )}
      >
        <Kaboom message="specific" />
      </SectionErrorBoundary>,
    );
    expect(screen.getByTestId('custom-fallback')).toHaveTextContent(
      'custom: specific',
    );
  });
});
