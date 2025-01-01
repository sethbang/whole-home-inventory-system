# eBay Integration Feature

## Overview

The eBay integration feature enables users to export their WHIS inventory items directly to eBay for listing. This feature is being implemented in two phases to provide immediate value while building towards a fully automated solution.

## Current Implementation Status

### Completed Features
- eBay-specific fields integration in item details
- React components for eBay listing configuration
- Category lookup functionality
- Basic field validation
- Test coverage for components and API

### Components
1. **EbayFields Component** (`frontend/src/components/EbayFields.tsx`)
   - Manages eBay-specific listing details
   - Supports listing format selection (Auction/Fixed Price)
   - Handles condition selection
   - Manages pricing options
   - Configures shipping settings
   - Handles returns policy
   - Supports payment methods

2. **eBay API Client** (`frontend/src/api/ebay.ts`)
   - Category lookup functionality
   - Field updates
   - Export preparation

3. **Backend Integration** (`backend/app/ebay/`)
   - Category mapping system
   - Schema definitions
   - API endpoints

### Data Structure
The eBay fields are stored in the item's custom_fields object:
```typescript
interface EbayFieldsData {
  category_id?: string;
  condition?: 'NEW' | 'LIKE_NEW' | 'VERY_GOOD' | 'GOOD' | 'ACCEPTABLE' | 'FOR_PARTS';
  listing_format?: 'FIXED_PRICE' | 'AUCTION';
  duration?: 'DAYS_3' | 'DAYS_5' | 'DAYS_7' | 'DAYS_10' | 'DAYS_30' | 'GTC';
  shipping_service?: 'USPS_FIRST_CLASS' | 'USPS_PRIORITY' | 'USPS_GROUND' | 'UPS_GROUND' | 'FEDEX_GROUND' | 'FREIGHT' | 'LOCAL_PICKUP';
  shipping_cost?: number;
  returns_accepted?: boolean;
  return_period?: 'DAYS_30' | 'DAYS_60' | 'NO_RETURNS';
  payment_methods?: Array<'PAYPAL' | 'CREDIT_CARD' | 'BANK_TRANSFER'>;
  starting_price?: number;
  reserve_price?: number;
  buy_it_now_price?: number;
  quantity?: number;
  domestic_shipping_only?: boolean;
  item_specifics?: Record<string, string>;
}
```

## Next Steps

### Immediate Priorities
1. **Bulk Export Implementation**
   - Create bulk selection interface
   - Implement CSV export format
   - Add export progress tracking
   - Support batch processing

2. **Category Mapping Enhancement**
   - Improve category suggestions
   - Add category search
   - Support subcategories
   - Cache common categories

3. **Image Integration**
   - Implement image URL generation
   - Add image order management
   - Support eBay image requirements
   - Handle image optimization

### Future Enhancements (Phase 2)
1. **Direct API Integration**
   - OAuth implementation
   - Real-time listing creation
   - Inventory synchronization
   - Order management

2. **Advanced Features**
   - Listing templates
   - Bulk pricing rules
   - Automated category mapping
   - Performance analytics

## Testing

### Component Tests
- `frontend/src/components/__tests__/EbayFields.test.tsx`
  - Field population
  - User interactions
  - Validation behavior
  - State management

### Integration Tests
- `frontend/src/pages/__tests__/ItemDetail.test.tsx`
  - eBay fields integration
  - Category lookup
  - Form submission
  - API interactions

### API Tests
- `frontend/src/api/__tests__/ebay.test.ts`
  - API client methods
  - Error handling
  - Response parsing

## Configuration

### Required Settings
- eBay category mappings
- Default listing settings
- Image URL base path
- Export preferences

### Optional Settings
- Default shipping options
- Return policy defaults
- Payment preferences

## Security Considerations

- Secure storage of eBay credentials (Phase 2)
- Safe handling of listing data
- Protected image access
- Rate limiting for API calls

## Current Limitations

1. Manual CSV upload required
2. No real-time sync
3. Limited automation
4. Basic error handling

These limitations will be addressed in Phase 2 through direct API integration.

## Development Guidelines

1. **Component Updates**
   - Follow existing component patterns
   - Maintain type safety
   - Include test coverage
   - Document changes

2. **API Integration**
   - Use existing client structure
   - Handle errors gracefully
   - Include retry logic
   - Validate responses

3. **Testing**
   - Write tests for new features
   - Update existing tests as needed
   - Include error cases
   - Test edge conditions

## Resources

- [eBay Developer Documentation](https://developer.ebay.com/docs)
- [Inventory API Reference](https://developer.ebay.com/api-docs/sell/inventory/resources/methods)
- [Category API Reference](https://developer.ebay.com/api-docs/commerce/taxonomy/resources/methods)