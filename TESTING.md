# WHIS Testing Guide

This document outlines the testing strategy, procedures, and best practices for the WHIS (Whole-Home Inventory System) project.

## Table of Contents

1. [Testing Overview](#testing-overview)
2. [Test Environment Setup](#test-environment-setup)
3. [Backend Testing](#backend-testing)
4. [Frontend Testing](#frontend-testing)
5. [End-to-End Testing](#end-to-end-testing)
6. [Performance Testing](#performance-testing)
7. [Security Testing](#security-testing)
8. [Continuous Integration](#continuous-integration)

## Testing Overview

### Testing Pyramid

WHIS follows the testing pyramid approach:
- Many unit tests (fast, isolated)
- Fewer integration tests (slower, dependencies)
- Few end-to-end tests (slowest, full system)

### Coverage Requirements

- Backend: Minimum 80% code coverage
- Frontend: Minimum 70% code coverage
- Critical paths: 100% coverage

### Test Types

1. **Unit Tests**
   - Individual components/functions
   - Mocked dependencies
   - Fast execution

2. **Integration Tests**
   - Component interactions
   - Database operations
   - API endpoints

3. **End-to-End Tests**
   - Full user workflows
   - Browser automation
   - Real environment

## Test Environment Setup

### Backend Test Setup

1. **Install Dependencies**
```bash
cd backend
pip install -r requirements-test.txt
```

2. **Test Database**
```bash
# Create test database
alembic upgrade head

# Create test data
python create_test_data.py
```

3. **Environment Variables**
```bash
export TESTING=true
export TEST_DATABASE_URL=sqlite:///./test.db
```

### Frontend Test Setup

1. **Install Dependencies**
```bash
cd frontend
npm install --save-dev @testing-library/react @testing-library/jest-dom
```

2. **Test Configuration**
```javascript
// jest.config.js
module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/src/setupTests.ts'],
  moduleNameMapper: {
    '\\.(css|less|scss)$': 'identity-obj-proxy',
    '\\.(jpg|jpeg|png|gif|svg)$': '<rootDir>/__mocks__/fileMock.js'
  }
};
```

## Backend Testing

### Unit Tests

1. **Models Testing**
```python
# tests/test_models.py
import pytest
from app.models import Item

def test_item_creation():
    item = Item(
        name="Test Item",
        category="Test",
        location="Test Location"
    )
    assert item.name == "Test Item"
    assert item.category == "Test"
```

2. **API Testing**
```python
# tests/test_api.py
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

3. **Service Testing**
```python
# tests/test_services.py
import pytest
from app.services import ItemService

def test_item_service():
    service = ItemService()
    item = service.create_item({
        "name": "Test Item",
        "category": "Test"
    })
    assert item is not None
```

### Integration Tests

1. **Database Integration**
```python
# tests/test_db_integration.py
import pytest
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Item

def test_database_operations():
    db = next(get_db())
    item = Item(name="Test", category="Test")
    db.add(item)
    db.commit()
    
    fetched = db.query(Item).first()
    assert fetched.name == "Test"
```

2. **API Integration**
```python
# tests/test_api_integration.py
def test_item_workflow():
    # Create item
    create_response = client.post("/api/items/", json={...})
    item_id = create_response.json()["id"]
    
    # Update item
    update_response = client.put(f"/api/items/{item_id}", json={...})
    
    # Delete item
    delete_response = client.delete(f"/api/items/{item_id}")
    
    assert delete_response.status_code == 204
```

## Frontend Testing

### Component Tests

1. **Render Testing**
```typescript
// src/components/__tests__/ItemList.test.tsx
import { render, screen } from '@testing-library/react';
import { ItemList } from '../ItemList';

describe('ItemList', () => {
  it('renders items correctly', () => {
    const items = [
      { id: '1', name: 'Test Item', category: 'Test' }
    ];
    
    render(<ItemList items={items} />);
    expect(screen.getByText('Test Item')).toBeInTheDocument();
  });
});
```

2. **User Interaction**
```typescript
// src/components/__tests__/AddItem.test.tsx
import { render, fireEvent } from '@testing-library/react';
import { AddItem } from '../AddItem';

test('form submission', async () => {
  const onSubmit = jest.fn();
  const { getByLabelText, getByText } = render(
    <AddItem onSubmit={onSubmit} />
  );
  
  fireEvent.change(getByLabelText('Name'), {
    target: { value: 'Test Item' }
  });
  
  fireEvent.click(getByText('Submit'));
  expect(onSubmit).toHaveBeenCalled();
});
```

3. **Hook Testing**
```typescript
// src/hooks/__tests__/useItems.test.tsx
import { renderHook, act } from '@testing-library/react-hooks';
import { useItems } from '../useItems';

test('useItems hook', async () => {
  const { result } = renderHook(() => useItems());
  
  act(() => {
    result.current.addItem({ name: 'Test' });
  });
  
  expect(result.current.items).toHaveLength(1);
});
```

### Integration Tests

1. **API Integration**
```typescript
// src/api/__tests__/client.test.ts
import { APIClient } from '../client';

describe('API Client', () => {
  it('fetches items', async () => {
    const client = new APIClient();
    const items = await client.getItems();
    expect(items).toBeDefined();
  });
});
```

2. **Component Integration**
```typescript
// src/pages/__tests__/Dashboard.test.tsx
test('dashboard integration', async () => {
  render(
    <AuthProvider>
      <Dashboard />
    </AuthProvider>
  );
  
  await waitFor(() => {
    expect(screen.getByText('Items')).toBeInTheDocument();
  });
});
```

## End-to-End Testing

### Playwright Tests

1. **Test Setup**
```typescript
// e2e/setup.ts
import { test as base } from '@playwright/test';

export const test = base.extend({
  page: async ({ page }, use) => {
    await page.goto('http://localhost:5173');
    await use(page);
  }
});
```

2. **User Flows**
```typescript
// e2e/itemFlow.spec.ts
test('complete item workflow', async ({ page }) => {
  // Login
  await page.fill('[data-testid="username"]', 'testuser');
  await page.fill('[data-testid="password"]', 'password');
  await page.click('button[type="submit"]');
  
  // Add item
  await page.click('[data-testid="add-item"]');
  await page.fill('[data-testid="item-name"]', 'Test Item');
  await page.click('[data-testid="submit"]');
  
  // Verify item
  await expect(page.locator('text=Test Item')).toBeVisible();
});
```

## Performance Testing

### Backend Performance

1. **Load Testing**
```python
# tests/performance/test_load.py
from locust import HttpUser, task, between

class WHISUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def get_items(self):
        self.client.get("/api/items/")
```

2. **Database Performance**
```python
# tests/performance/test_db.py
import time

def test_query_performance():
    start = time.time()
    items = db.query(Item).all()
    duration = time.time() - start
    
    assert duration < 0.1  # 100ms threshold
```

### Frontend Performance

1. **Component Performance**
```typescript
// src/components/__tests__/performance.test.tsx
import { Profiler } from 'react';

test('component render performance', () => {
  const onRender = jest.fn();
  
  render(
    <Profiler id="test" onRender={onRender}>
      <ItemList items={items} />
    </Profiler>
  );
  
  const [duration] = onRender.mock.calls[0];
  expect(duration).toBeLessThan(16);  // 60fps threshold
});
```

## Security Testing

### Authentication Tests

```python
# tests/security/test_auth.py
def test_invalid_token():
    response = client.get(
        "/api/items/",
        headers={"Authorization": "Bearer invalid"}
    )
    assert response.status_code == 401

def test_password_hashing():
    from app.security import hash_password, verify_password
    
    password = "test_password"
    hashed = hash_password(password)
    assert verify_password(password, hashed)
```

### Input Validation Tests

```python
# tests/security/test_validation.py
def test_xss_prevention():
    response = client.post(
        "/api/items/",
        json={"name": "<script>alert('xss')</script>"}
    )
    assert "<script>" not in response.json()["name"]
```

## Continuous Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Run tests
      run: |
        pytest --cov=app tests/
        coverage report --fail-under=80
```

## Best Practices

1. **Test Organization**
   - Group related tests
   - Use descriptive names
   - Follow AAA pattern (Arrange, Act, Assert)
   - Keep tests independent

2. **Test Data**
   - Use factories/fixtures
   - Avoid hard-coded values
   - Clean up after tests
   - Use realistic data

3. **Assertions**
   - Be specific
   - Test one thing per test
   - Use appropriate matchers
   - Include error messages

4. **Maintenance**
   - Keep tests up to date
   - Remove obsolete tests
   - Refactor when needed
   - Document complex tests

## Running Tests

### Backend Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_items.py

# Run with verbose output
pytest -v
```

### Frontend Tests
```bash
# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Run specific test file
npm test ItemList.test.tsx

# Watch mode
npm test -- --watch
```

### End-to-End Tests
```bash
# Install Playwright
npx playwright install

# Run all E2E tests
npx playwright test

# Run specific test file
npx playwright test itemFlow.spec.ts

# Run with UI
npx playwright test --ui