# WHIS Development Guide

This guide provides detailed information for developers working on the WHIS (Whole-Home Inventory System) project.

## Table of Contents

1. [Development Environment Setup](#development-environment-setup)
2. [Project Structure](#project-structure)
3. [Development Workflow](#development-workflow)
4. [Code Style and Standards](#code-style-and-standards)
5. [Testing](#testing)
6. [Debugging](#debugging)
7. [Performance Optimization](#performance-optimization)
8. [Common Development Tasks](#common-development-tasks)

## Development Environment Setup

### Prerequisites

- Python 3.11+
- Node.js 16+
- Git
- VS Code (recommended)
- Docker (optional)

### VS Code Extensions

Recommended extensions for development:
- Python
- Pylance
- ESLint
- Prettier
- TypeScript and JavaScript
- Tailwind CSS IntelliSense
- Docker
- SQLite Viewer

### Environment Setup Steps

1. **Clone and Setup**
```bash
# Clone repository
git clone https://github.com/yourusername/whis.git
cd whis

# Create Python virtual environment
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Install frontend dependencies
cd ../frontend
npm install
```

2. **Development Certificates**
```bash
# Generate certificates
cd frontend
node scripts/generate-certs.js

# Install certificates (see CERTIFICATE-SETUP.md for OS-specific instructions)
```

3. **Database Setup**
```bash
cd ../backend
alembic upgrade head
python create_dev_user.py  # Creates a development user account
```

4. **IDE Configuration**

VS Code settings.json:
```json
{
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "typescript.preferences.importModuleSpecifier": "relative"
}
```

## Project Structure

### Backend Structure
```
backend/
├── alembic/              # Database migrations
├── app/
│   ├── routers/         # API route handlers
│   ├── models.py        # SQLAlchemy models
│   ├── schemas.py       # Pydantic schemas
│   ├── database.py      # Database configuration
│   ├── security.py      # Authentication/authorization
│   └── main.py          # FastAPI application
├── tests/               # Test files
└── requirements.txt     # Python dependencies
```

### Frontend Structure
```
frontend/
├── src/
│   ├── api/            # API client and types
│   ├── components/     # React components
│   ├── contexts/       # React contexts
│   ├── pages/         # Page components
│   ├── assets/        # Static assets
│   └── App.tsx        # Root component
├── public/            # Static files
└── package.json       # Node.js dependencies
```

## Development Workflow

### Starting Development Servers

1. **Backend Server**
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 27182
```

2. **Frontend Server**
```bash
cd frontend
npm run dev
```

### Database Migrations

1. **Create a Migration**
```bash
cd backend
alembic revision -m "description_of_changes"
```

2. **Edit Migration File**
```python
# backend/alembic/versions/xxxx_description_of_changes.py
def upgrade():
    # Add upgrade changes
    pass

def downgrade():
    # Add downgrade changes
    pass
```

3. **Apply Migration**
```bash
alembic upgrade head
```

4. **Revert Migration**
```bash
alembic downgrade -1  # Revert last migration
```

### Working with TypeScript Types

1. **API Types**
```typescript
// frontend/src/api/types.ts
export interface Item {
  id: string;
  name: string;
  category: string;
  // ... other fields
}
```

2. **Component Props**
```typescript
// frontend/src/components/ItemList.tsx
interface ItemListProps {
  items: Item[];
  onItemClick: (item: Item) => void;
}
```

## Code Style and Standards

### Python Style Guide

- Follow PEP 8
- Use type hints
- Maximum line length: 88 characters (Black)
- Sort imports with isort
- Use docstrings for functions and classes

Example:
```python
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Item
from app.schemas import ItemCreate

def create_item(
    db: Session,
    item: ItemCreate,
    user_id: str
) -> Item:
    """
    Create a new inventory item.

    Args:
        db: Database session
        item: Item data
        user_id: ID of the creating user

    Returns:
        Created item instance

    Raises:
        HTTPException: If item creation fails
    """
    db_item = Item(**item.dict(), user_id=user_id)
    db.add(db_item)
    try:
        db.commit()
        db.refresh(db_item)
        return db_item
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
```

### TypeScript/React Style Guide

- Use functional components
- Use TypeScript types/interfaces
- Follow ESLint configuration
- Use React Hooks guidelines
- Maximum line length: 80 characters

Example:
```typescript
import React, { useState, useEffect } from 'react';
import { Item } from '../api/types';
import { useAuth } from '../contexts/AuthContext';

interface ItemListProps {
  category?: string;
  onItemSelect: (item: Item) => void;
}

export const ItemList: React.FC<ItemListProps> = ({
  category,
  onItemSelect,
}) => {
  const [items, setItems] = useState<Item[]>([]);
  const { api } = useAuth();

  useEffect(() => {
    const fetchItems = async () => {
      const response = await api.getItems({ category });
      setItems(response.data);
    };

    fetchItems();
  }, [category, api]);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {items.map((item) => (
        <div
          key={item.id}
          onClick={() => onItemSelect(item)}
          className="p-4 border rounded hover:shadow-lg"
        >
          <h3 className="text-lg font-semibold">{item.name}</h3>
          <p className="text-gray-600">{item.category}</p>
        </div>
      ))}
    </div>
  );
};
```

## Testing

### Backend Testing

1. **Unit Tests**
```python
# backend/tests/test_items.py
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_create_item():
    response = client.post(
        "/api/items/",
        json={
            "name": "Test Item",
            "category": "Test",
            "location": "Test Location"
        },
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Test Item"
```

2. **Running Tests**
```bash
cd backend
pytest
pytest --cov=app tests/  # With coverage
```

### Frontend Testing

1. **Component Tests**
```typescript
// frontend/src/components/__tests__/ItemList.test.tsx
import { render, screen } from '@testing-library/react';
import { ItemList } from '../ItemList';

describe('ItemList', () => {
  it('renders items correctly', () => {
    const items = [
      { id: '1', name: 'Test Item', category: 'Test' }
    ];
    
    render(<ItemList items={items} onItemSelect={() => {}} />);
    
    expect(screen.getByText('Test Item')).toBeInTheDocument();
  });
});
```

2. **Running Tests**
```bash
cd frontend
npm test
npm run test:coverage  # With coverage
```

## Debugging

### Backend Debugging

1. **VS Code Launch Configuration**
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["app.main:app", "--reload"],
      "jinja": true,
      "justMyCode": true
    }
  ]
}
```

2. **Debug Logging**
```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug("Debug message")
logger.info("Info message")
logger.error("Error message")
```

### Frontend Debugging

1. **React Developer Tools**
- Install Chrome/Firefox extension
- Use Components tab for component inspection
- Use Profiler tab for performance analysis

2. **Console Logging**
```typescript
// Development-only logging
if (process.env.NODE_ENV === 'development') {
  console.log('Debug:', data);
}
```

## Performance Optimization

### Backend Optimization

1. **Database Optimization**
- Use appropriate indexes
- Optimize queries
- Use pagination
- Cache frequent queries

2. **API Optimization**
- Use async/await
- Implement caching
- Optimize response payload
- Use compression

### Frontend Optimization

1. **React Optimization**
- Use React.memo for expensive components
- Implement virtualization for long lists
- Optimize images
- Use code splitting

2. **Build Optimization**
- Enable tree shaking
- Use production builds
- Implement caching
- Optimize bundle size

## Common Development Tasks

### Adding a New Feature

1. Create a new branch
2. Update database schema if needed
3. Create/update API endpoints
4. Add frontend components
5. Write tests
6. Update documentation
7. Create pull request

### Updating Dependencies

1. **Backend Dependencies**
```bash
cd backend
pip list --outdated
pip install --upgrade package-name
```

2. **Frontend Dependencies**
```bash
cd frontend
npm outdated
npm update
```

### Building for Production

1. **Backend**
```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
```

2. **Frontend**
```bash
cd frontend
npm install
npm run build
```

### Troubleshooting

1. **Backend Issues**
- Check logs
- Verify database connection
- Check API responses
- Validate environment variables

2. **Frontend Issues**
- Check console errors
- Verify API endpoints
- Check network requests
- Validate build output

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://reactjs.org/)
- [TypeScript Documentation](https://www.typescriptlang.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Tailwind CSS Documentation](https://tailwindcss.com/)