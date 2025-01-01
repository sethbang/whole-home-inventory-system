# WHIS API Documentation

This document provides comprehensive documentation for the WHIS (Whole-Home Inventory System) REST API.

## Base URL

- Development: `https://localhost:27182`
- Production: `https://[your-server]:27182`

## Authentication

WHIS uses JWT (JSON Web Token) authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your_jwt_token>
```

### Authentication Endpoints

#### POST /api/auth/login
Login with username and password.

**Request:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "access_token": "string",
  "token_type": "bearer"
}
```

#### POST /api/auth/register
Register a new user (only available if no users exist).

**Request:**
```json
{
  "username": "string",
  "password": "string",
  "email": "string"
}
```

**Response:**
```json
{
  "id": "uuid",
  "username": "string",
  "email": "string"
}
```

## Items API

### Item Object

```json
{
  "id": "uuid",
  "name": "string",
  "category": "string",
  "location": "string",
  "brand": "string",
  "model_number": "string",
  "serial_number": "string",
  "barcode": "string",
  "purchase_date": "YYYY-MM-DD",
  "purchase_price": "number",
  "current_value": "number",
  "warranty_expiration": "YYYY-MM-DD",
  "notes": "string",
  "custom_fields": {
    "field_name": "value"
  },
  "images": [
    {
      "id": "uuid",
      "url": "string",
      "filename": "string",
      "created_at": "datetime"
    }
  ],
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### Endpoints

#### GET /api/items
Get all items with optional filtering.

**Query Parameters:**
- `category` (string): Filter by category
- `location` (string): Filter by location
- `search` (string): Search in name, notes, and custom fields
- `sort` (string): Sort field (name, category, location, created_at, updated_at)
- `order` (string): Sort order (asc, desc)
- `page` (integer): Page number for pagination
- `limit` (integer): Items per page (default: 50)

**Response:**
```json
{
  "items": [Item],
  "total": "integer",
  "page": "integer",
  "pages": "integer"
}
```

#### POST /api/items
Create a new item.

**Request Body:** Item object (without id, created_at, updated_at)

**Response:** Created Item object

#### GET /api/items/{item_id}
Get a specific item by ID.

**Response:** Item object

#### PUT /api/items/{item_id}
Update an existing item.

**Request Body:** Item object (without id, created_at, updated_at)

**Response:** Updated Item object

#### DELETE /api/items/{item_id}
Delete an item.

**Response:** 204 No Content

## Images API

### Image Object

```json
{
  "id": "uuid",
  "item_id": "uuid",
  "filename": "string",
  "url": "string",
  "created_at": "datetime"
}
```

### Endpoints

#### POST /api/items/{item_id}/images
Upload images for an item.

**Request Body:** Form data with image file(s)
- `images`: Array of image files (multipart/form-data)

**Response:**
```json
{
  "images": [Image]
}
```

#### DELETE /api/items/{item_id}/images/{image_id}
Delete an image.

**Response:** 204 No Content

## Analytics API

### Endpoints

#### GET /api/analytics/summary
Get inventory summary statistics.

**Response:**
```json
{
  "total_items": "integer",
  "total_value": "number",
  "items_by_category": {
    "category": "count"
  },
  "items_by_location": {
    "location": "count"
  }
}
```

#### GET /api/analytics/value-history
Get historical value tracking.

**Query Parameters:**
- `period` (string): Time period (week, month, year)

**Response:**
```json
{
  "periods": ["date"],
  "values": ["number"]
}
```

## Backup API

### Endpoints

#### POST /api/backups/create
Create a new backup.

**Response:**
```json
{
  "id": "uuid",
  "filename": "string",
  "size": "integer",
  "created_at": "datetime"
}
```

#### GET /api/backups
List available backups.

**Response:**
```json
{
  "backups": [
    {
      "id": "uuid",
      "filename": "string",
      "size": "integer",
      "created_at": "datetime"
    }
  ]
}
```

#### POST /api/backups/{backup_id}/restore
Restore from a backup.

**Response:**
```json
{
  "success": "boolean",
  "message": "string"
}
```

#### GET /api/backups/{backup_id}/download
Download a backup file.

**Response:** Backup file (application/octet-stream)

## Data Migration API

### Endpoints

#### POST /api/migration/import
Import items from CSV or JSON.

**Request Body:** Form data
- `file`: CSV or JSON file
- `format`: "csv" or "json"

**Response:**
```json
{
  "imported": "integer",
  "errors": [
    {
      "row": "integer",
      "message": "string"
    }
  ]
}
```

#### GET /api/migration/export
Export items to CSV or JSON.

**Query Parameters:**
- `format` (string): "csv" or "json"

**Response:** File download (text/csv or application/json)

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
  "detail": "Error message explaining the problem"
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden
```json
{
  "detail": "Not enough privileges"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["field_name"],
      "msg": "Error message",
      "type": "error_type"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

## Rate Limiting

- Rate limit: 100 requests per minute per IP
- Rate limit headers included in responses:
  - `X-RateLimit-Limit`
  - `X-RateLimit-Remaining`
  - `X-RateLimit-Reset`

## Versioning

The API version is included in the response headers:
- `X-API-Version`: Current API version

## Best Practices

1. **Authentication**
   - Store JWT tokens securely
   - Refresh tokens before expiration
   - Include tokens in all authenticated requests

2. **Error Handling**
   - Implement proper error handling
   - Check for specific error types
   - Handle rate limiting appropriately

3. **Performance**
   - Use pagination for large datasets
   - Minimize request frequency
   - Cache responses when appropriate

4. **Security**
   - Use HTTPS for all requests
   - Validate input data
   - Handle sensitive data securely

## Examples

### Curl Examples

#### Login
```bash
curl -X POST https://localhost:27182/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}'
```

#### Get Items
```bash
curl https://localhost:27182/api/items \
  -H "Authorization: Bearer <token>"
```

#### Create Item
```bash
curl -X POST https://localhost:27182/api/items \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Example Item",
    "category": "Electronics",
    "location": "Office"
  }'
```

### Python Example

```python
import requests

class WHISClient:
    def __init__(self, base_url, token=None):
        self.base_url = base_url
        self.token = token
        
    def login(self, username, password):
        response = requests.post(
            f"{self.base_url}/api/auth/login",
            json={"username": username, "password": password}
        )
        self.token = response.json()["access_token"]
        
    def get_items(self, **params):
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(
            f"{self.base_url}/api/items",
            headers=headers,
            params=params
        )
        return response.json()
        
    def create_item(self, item_data):
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.post(
            f"{self.base_url}/api/items",
            headers=headers,
            json=item_data
        )
        return response.json()
```

### TypeScript Example

```typescript
interface WHISConfig {
  baseUrl: string;
  token?: string;
}

class WHISClient {
  private baseUrl: string;
  private token?: string;

  constructor(config: WHISConfig) {
    this.baseUrl = config.baseUrl;
    this.token = config.token;
  }

  async login(username: string, password: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    const data = await response.json();
    this.token = data.access_token;
  }

  async getItems(params: Record<string, string> = {}): Promise<any> {
    const queryString = new URLSearchParams(params).toString();
    const response = await fetch(
      `${this.baseUrl}/api/items?${queryString}`,
      {
        headers: {
          Authorization: `Bearer ${this.token}`
        }
      }
    );
    return response.json();
  }

  async createItem(itemData: Record<string, any>): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/items`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(itemData)
    });
    return response.json();
  }
}
```

## Support

For API support and questions:
1. Check the documentation thoroughly
2. Search existing issues on GitHub
3. Open a new issue if needed

## Changelog

See CHANGELOG.md for API version history and changes.