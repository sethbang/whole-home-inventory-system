# WHIS Frontend

This is the frontend application for the Whole Home Inventory System (WHIS), built with React, TypeScript, and Vite.

## Docker Development Setup

1. Stop any running containers:
```bash
docker compose down
```

2. Rebuild and start the containers:
```bash
docker compose up --build
```

The frontend will be available at `https://localhost:5173` or your local IP (e.g., `https://192.168.1.15:5173`).

### HTTPS Certificate

The development server uses HTTPS with a self-signed certificate. When you first access the site:

1. You'll see a security warning in your browser - this is normal for self-signed certificates
2. In Chrome/Edge: Click "Advanced" and then "Proceed to localhost (unsafe)"
3. In Safari: Click "Show Details" and then "visit this website"
4. In iOS Safari: Go to Settings > General > About > Certificate Trust Settings, and enable trust for the development certificate

This HTTPS setup is required for:
- Camera access on iOS devices
- Testing PWA features
- Secure cookie handling

## Local Development Setup

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

The development server will:
- Generate self-signed HTTPS certificates (required for camera access on iOS)
- Start Vite in development mode with HTTPS enabled
- Listen on all network interfaces (accessible via local IP)

### HTTPS Certificate

The development server uses HTTPS with a self-signed certificate. When you first access the site:

1. You'll see a security warning in your browser - this is normal for self-signed certificates
2. In Chrome/Edge: Click "Advanced" and then "Proceed to localhost (unsafe)"
3. In Safari: Click "Show Details" and then "visit this website"
4. In iOS Safari: Go to Settings > General > About > Certificate Trust Settings, and enable trust for the development certificate

This HTTPS setup is required for:
- Camera access on iOS devices
- Testing PWA features
- Secure cookie handling

## ESLint Configuration

If you are developing a production application, we recommend updating the configuration to enable type aware lint rules:

- Configure the top-level `parserOptions` property like this:

```js
export default tseslint.config({
  languageOptions: {
    parserOptions: {
      project: ['./tsconfig.node.json', './tsconfig.app.json'],
      tsconfigRootDir: import.meta.dirname,
    },
  },
})
```

- Replace `tseslint.configs.recommended` to `tseslint.configs.recommendedTypeChecked` or `tseslint.configs.strictTypeChecked`
- Optionally add `...tseslint.configs.stylisticTypeChecked`
- Install [eslint-plugin-react](https://github.com/jsx-eslint/eslint-plugin-react) and update the config:

```js
// eslint.config.js
import react from 'eslint-plugin-react'

export default tseslint.config({
  // Set the react version
  settings: { react: { version: '18.3' } },
  plugins: {
    // Add the react plugin
    react,
  },
  rules: {
    // Enable its recommended rules
    ...react.configs.recommended.rules,
    ...react.configs['jsx-runtime'].rules,
  },
})
