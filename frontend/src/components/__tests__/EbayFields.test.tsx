import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import EbayFields, { EbayFieldsData } from '../EbayFields';

describe('EbayFields', () => {
  const mockOnChange = jest.fn();
  const defaultProps = {
    fields: {} as EbayFieldsData,
    onChange: mockOnChange,
  };

  beforeEach(() => {
    mockOnChange.mockClear();
  });

  it('renders all form fields', () => {
    render(<EbayFields {...defaultProps} />);
    
    // Check for main form fields
    expect(screen.getByLabelText(/listing format/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/condition/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/duration/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/quantity/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/shipping service/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/shipping cost/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/accept returns/i)).toBeInTheDocument();
  });

  it('shows auction-specific fields when listing format is AUCTION', () => {
    render(
      <EbayFields
        {...defaultProps}
        fields={{ listing_format: 'AUCTION' }}
      />
    );

    expect(screen.getByLabelText(/starting price/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/reserve price/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/buy it now price/i)).not.toBeInTheDocument();
  });

  it('shows fixed price fields when listing format is FIXED_PRICE', () => {
    render(
      <EbayFields
        {...defaultProps}
        fields={{ listing_format: 'FIXED_PRICE' }}
      />
    );

    expect(screen.getByLabelText(/buy it now price/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/starting price/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/reserve price/i)).not.toBeInTheDocument();
  });

  it('shows return period field when returns are accepted', () => {
    render(
      <EbayFields
        {...defaultProps}
        fields={{ returns_accepted: true }}
      />
    );

    expect(screen.getByLabelText(/return period/i)).toBeInTheDocument();
  });

  it('calls onChange when fields are updated', () => {
    render(<EbayFields {...defaultProps} />);

    // Test updating listing format
    fireEvent.change(screen.getByLabelText(/listing format/i), {
      target: { value: 'FIXED_PRICE' }
    });

    expect(mockOnChange).toHaveBeenCalledWith(
      expect.objectContaining({
        listing_format: 'FIXED_PRICE'
      })
    );

    // Test updating condition
    fireEvent.change(screen.getByLabelText(/condition/i), {
      target: { value: 'NEW' }
    });

    expect(mockOnChange).toHaveBeenCalledWith(
      expect.objectContaining({
        condition: 'NEW'
      })
    );

    // Test updating shipping cost
    fireEvent.change(screen.getByLabelText(/shipping cost/i), {
      target: { value: '10.99' }
    });

    expect(mockOnChange).toHaveBeenCalledWith(
      expect.objectContaining({
        shipping_cost: 10.99
      })
    );
  });

  it('handles payment method checkboxes correctly', () => {
    let currentFields: EbayFieldsData = {};
    const mockOnChangeWithState = (newFields: EbayFieldsData) => {
      currentFields = newFields;
      mockOnChange(newFields);
    };

    const { rerender } = render(
      <EbayFields
        {...defaultProps}
        fields={currentFields}
        onChange={mockOnChangeWithState}
      />
    );

    // Click PayPal checkbox
    const paypalCheckbox = screen.getByLabelText(/paypal/i);
    fireEvent.click(paypalCheckbox);

    // Re-render with updated fields
    rerender(
      <EbayFields
        {...defaultProps}
        fields={currentFields}
        onChange={mockOnChangeWithState}
      />
    );

    // Click Credit Card checkbox
    const creditCardCheckbox = screen.getByLabelText(/credit card/i);
    fireEvent.click(creditCardCheckbox);

    // Verify final state includes both payment methods
    expect(currentFields.payment_methods).toEqual(['PAYPAL', 'CREDIT_CARD']);
  });

  it('handles domestic shipping checkbox correctly', () => {
    render(<EbayFields {...defaultProps} />);

    const checkbox = screen.getByLabelText(/domestic shipping only/i);
    
    fireEvent.click(checkbox);
    expect(mockOnChange).toHaveBeenCalledWith(
      expect.objectContaining({
        domestic_shipping_only: true
      })
    );
  });

  it('shows category lookup button when onCategoryLookup is provided', () => {
    const onCategoryLookup = jest.fn();
    render(<EbayFields {...defaultProps} onCategoryLookup={onCategoryLookup} />);

    const lookupButton = screen.getByText('Look Up');
    expect(lookupButton).toBeInTheDocument();

    fireEvent.click(lookupButton);
    expect(onCategoryLookup).toHaveBeenCalled();
  });
});