import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

import FacebookFields from '../FacebookFields';
import type { FbFieldsData } from '../../api/types';

describe('FacebookFields', () => {
  const renderComponent = (overrides: Partial<FbFieldsData> = {}) => {
    const onChange = vi.fn();
    render(
      <FacebookFields
        fields={overrides}
        categories={['Tools', 'Furniture', 'Miscellaneous']}
        onChange={onChange}
      />,
    );
    return { onChange };
  };

  it('renders all core fields', () => {
    renderComponent();
    expect(screen.getByLabelText(/listing price/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/condition/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/facebook category/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/description override/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/available \(in stock\)/i)).toBeInTheDocument();
  });

  it('emits a parsed number when the price input changes', () => {
    const { onChange } = renderComponent();
    fireEvent.change(screen.getByLabelText(/listing price/i), {
      target: { value: '42.50' },
    });
    expect(onChange).toHaveBeenLastCalledWith({ price: 42.5 });
  });

  it('clears price back to undefined when the field is emptied', () => {
    const { onChange } = renderComponent({ price: 10 });
    fireEvent.change(screen.getByLabelText(/listing price/i), {
      target: { value: '' },
    });
    expect(onChange).toHaveBeenLastCalledWith({ price: undefined });
  });

  it('emits condition selections', () => {
    const { onChange } = renderComponent();
    fireEvent.change(screen.getByLabelText(/condition/i), {
      target: { value: 'USED_LIKE_NEW' },
    });
    expect(onChange).toHaveBeenLastCalledWith({ condition: 'USED_LIKE_NEW' });
  });

  it('availability toggle flips between in stock and out of stock', () => {
    const { onChange } = renderComponent({ availability: 'in stock' });
    fireEvent.click(screen.getByLabelText(/available \(in stock\)/i));
    expect(onChange).toHaveBeenLastCalledWith({ availability: 'out of stock' });
  });

  it('lists every category option passed in', () => {
    renderComponent();
    expect(screen.getByRole('option', { name: 'Tools' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Furniture' })).toBeInTheDocument();
    expect(
      screen.getByRole('option', { name: 'Miscellaneous' }),
    ).toBeInTheDocument();
  });
});
