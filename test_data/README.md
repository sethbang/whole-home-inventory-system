# Test Data Examples

This directory contains sample data files that can be used to test and demonstrate the WHIS (Whole Home Inventory System) functionality. These examples cover various scenarios and use cases to help users understand the system's capabilities.

## Directory Structure

- `samples/` - Contains various sample data files in different formats
  - `test_items.csv` - Basic CSV format example with common household items
  - `test_items.json` - Same data in JSON format
  - `office_inventory.csv` - Example of an office inventory setup
  - `home_electronics.json` - Focused example of electronics with detailed specifications
  - `garage_tools.csv` - Example of garage/workshop inventory
  - `collectibles.json` - Example showing collectible items with custom fields
  - `minimal_fields.csv` - Example with only required fields populated
  - `special_cases.json` - Examples of special characters, long descriptions, etc.

## File Formats

The system supports the following import formats:
- CSV (Comma-Separated Values)
- JSON (JavaScript Object Notation)

## Field Descriptions

### Required Fields
- `name` - Name/title of the item
- `category` - General category (e.g., Electronics, Furniture, Appliances)
- `location` - Where the item is stored/located

### Optional Fields
- `brand` - Manufacturer/brand name
- `model_number` - Model number or identifier
- `serial_number` - Unique serial number
- `barcode` - Product barcode (UPC, EAN, etc.)
- `purchase_date` - Date of purchase (YYYY-MM-DD format)
- `purchase_price` - Original purchase price
- `current_value` - Estimated current value
- `warranty_expiration` - Warranty expiration date (YYYY-MM-DD format)
- `notes` - Additional notes or description
- `custom_fields` - JSON object containing custom key-value pairs

## Usage

These sample files can be used to:
1. Test the import functionality
2. Understand the expected data format
3. See examples of different inventory scenarios
4. Learn how to structure your own inventory data

## Notes

- All dates should be in YYYY-MM-DD format
- Prices should be decimal numbers without currency symbols
- Custom fields should be valid JSON objects
- Empty/optional fields can be left blank in CSV or null in JSON