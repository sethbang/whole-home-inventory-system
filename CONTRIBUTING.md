# Contributing to WHIS (Whole-Home Inventory System)

Thank you for your interest in contributing to WHIS! This document provides comprehensive guidelines for contributing to the project.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Environment](#development-environment)
4. [Development Workflow](#development-workflow)
5. [Code Style Guidelines](#code-style-guidelines)
6. [Testing Guidelines](#testing-guidelines)
7. [Documentation Guidelines](#documentation-guidelines)
8. [Pull Request Process](#pull-request-process)
9. [Issue Guidelines](#issue-guidelines)
10. [Security Guidelines](#security-guidelines)

## Code of Conduct

We are committed to providing a welcoming and inclusive experience for everyone. By participating in this project, you agree to abide by our Code of Conduct.

- Be respectful and inclusive
- Exercise empathy and kindness
- Provide and accept constructive feedback
- Focus on what is best for the community

## Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/yourusername/whole-home-inventory-system
   cd whole-home-inventory-system
   ```
3. Set up your development environment (see below)
4. Create a new branch for your feature/fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Environment

### Prerequisites

- Python 3.11 or higher (CI tests 3.11 and 3.12)
- Node.js 20 or higher
- npm
- Git
- A code editor (VS Code recommended)

### Initial Setup

1. Set up the backend:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt

   # Copy env template and set a SECRET_KEY (required when BYPASS_AUTH=false)
   cp .env.example .env
   python -c "import secrets; print(secrets.token_urlsafe(64))"   # paste into SECRET_KEY

   # Apply migrations (use bootstrap.py so legacy stamps are reconciled)
   python scripts/bootstrap.py
   ```

2. Set up the frontend:
   ```bash
   cd frontend
   npm install
   ```

3. Set up development certificates:
   ```bash
   cd frontend
   node scripts/generate-certs.js
   ```
   Follow the certificate installation instructions in `certs/CERTIFICATE-SETUP.md`

### Running the Development Environment

1. Start the backend server:
   ```bash
   cd backend
   source venv/bin/activate
   uvicorn app.main:app --reload
   ```

2. Start the frontend development server:
   ```bash
   cd frontend
   npm run dev
   ```

## Development Workflow

1. **Create an Issue**
   - Search existing issues first
   - Use issue templates when available
   - Provide clear description and context

2. **Branch Creation**
   - Create a branch from `main`
   - Use descriptive branch names:
     - `feature/` for new features
     - `fix/` for bug fixes
     - `docs/` for documentation
     - `refactor/` for code refactoring
     - `test/` for test additions/modifications

3. **Development**
   - Write code following style guidelines
   - Include tests for new features
   - Update documentation as needed
   - Keep commits atomic and well-described

4. **Testing**
   - Run the test suite locally
   - Add new tests as needed
   - Ensure all tests pass
   - Test on different platforms if possible

5. **Documentation**
   - Update relevant documentation
   - Include inline code comments
   - Update API documentation if needed
   - Add examples for new features

6. **Pull Request**
   - Create a pull request against `main`
   - Fill out the PR template completely
   - Request review from maintainers
   - Address review feedback

## Code Style Guidelines

### Python (Backend)

- Follow PEP 8 style guide
- Use type hints
- Maximum line length: 88 characters (Black formatter)
- Use docstrings for functions and classes
- Sort imports using isort

### TypeScript/React (Frontend)

- Follow ESLint configuration
- Use TypeScript types/interfaces
- Use functional components
- Follow React Hooks guidelines
- Maximum line length: 80 characters
- Use JSDoc comments for complex functions

### General Guidelines

- Use meaningful variable and function names
- Keep functions small and focused
- Avoid deep nesting
- Write self-documenting code
- Include comments for complex logic

## Testing Guidelines

### Backend Testing

- Use pytest; `backend/tests/conftest.py` provides `client`, `user`, `auth_headers` fixtures against in-memory SQLite
- Test edge cases and error conditions
- Run locally with `pytest` before opening a PR; CI runs the same on Python 3.11 and 3.12
- Coverage targets (80%) are aspirational — not currently enforced by CI

### Frontend Testing

- Use React Testing Library + jest (preset `ts-jest`, jsdom)
- Write unit tests for components and API client modules under `**/__tests__/**/*.test.[jt]s?(x)`
- Run locally with `npm test` or `npm test -- --ci`

### End-to-End Testing

- Not currently present. Playwright or Cypress integration is deferred work — contributions welcome.

## Documentation Guidelines

### Code Documentation

- Use clear and concise comments
- Document complex algorithms
- Include usage examples
- Document known limitations
- Keep documentation up-to-date

### API Documentation

- Use OpenAPI/Swagger annotations
- Include request/response examples
- Document error responses
- Keep versioning information updated

### User Documentation

- Use clear, simple language
- Include screenshots where helpful
- Provide step-by-step guides
- Keep examples up-to-date

## Pull Request Process

1. **Before Submitting**
   - Update documentation
   - Add/update tests
   - Run linters and formatters
   - Test your changes thoroughly

2. **PR Description**
   - Reference related issues
   - Describe changes in detail
   - List breaking changes
   - Include screenshots if relevant

3. **Review Process**
   - Address reviewer feedback
   - Keep discussions focused
   - Update PR as needed
   - Maintain a clean commit history

4. **Merging**
   - Squash commits if needed
   - Ensure CI passes
   - Obtain required approvals
   - Delete branch after merge

## Issue Guidelines

### Bug Reports

Include:
- Clear description
- Steps to reproduce
- Expected vs actual behavior
- Environment details
- Screenshots if applicable

### Feature Requests

Include:
- Clear description of the need
- Use cases
- Proposed solution
- Alternative solutions considered
- Impact on existing features

## Security Guidelines

- Never commit sensitive data
- Report security issues privately
- Follow secure coding practices
- Keep dependencies updated
- Use environment variables for secrets

## Questions or Need Help?

- Check existing documentation
- Search closed issues
- Join our community discussions
- Contact maintainers

Thank you for contributing to WHIS! Your efforts help make this project better for everyone.