# 🛠️ **Development Environment Setup Guide**

## 📋 **Prerequisites**

### **System Requirements**
- **Node.js**: 18.0.0 or higher
- **npm**: 8.0.0 or higher
- **Git**: 2.30.0 or higher
- **Operating System**: Windows 10+, macOS 10.15+, or Ubuntu 18.04+

### **Recommended Tools**
- **IDE**: Visual Studio Code with recommended extensions
- **Browser**: Chrome, Firefox, Safari (latest versions)
- **Terminal**: PowerShell (Windows), Terminal (macOS), or Bash (Linux)

## 🚀 **Quick Start Setup**

### **Step 1: Clone Repository**
```bash
git clone <repository-url>
cd homeiq
```

### **Step 2: Install Dependencies**
```bash
# Install project dependencies
npm install

# Install Playwright for testing
npm install --save-dev @playwright/test
npx playwright install

# Install additional testing dependencies
npm install --save-dev @testing-library/react @testing-library/jest-dom
```

### **Step 3: Environment Configuration**
```bash
# Copy environment files
cp infrastructure/env.example .env.local
cp infrastructure/env.example .env.development

# Edit environment variables
# .env.local
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
VITE_APP_TITLE=Health Dashboard
```

### **Step 4: Start Development Server**
```bash
# Start the health dashboard
cd services/health-dashboard
npm run dev

# In another terminal, start the backend services
docker-compose up -d
```

## 🔧 **VS Code Setup**

### **Required Extensions**
```json
{
  "recommendations": [
    "ms-vscode.vscode-typescript-next",
    "bradlc.vscode-tailwindcss",
    "esbenp.prettier-vscode",
    "ms-vscode.vscode-json",
    "ms-playwright.playwright",
    "ms-vscode.vscode-eslint",
    "ms-vscode.vscode-react-snippets"
  ]
}
```

### **VS Code Settings**
```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  },
  "typescript.preferences.importModuleSpecifier": "relative",
  "tailwindCSS.includeLanguages": {
    "typescript": "typescript",
    "typescriptreact": "typescriptreact"
  }
}
```

### **Workspace Configuration**
```json
{
  "folders": [
    {
      "path": "."
    }
  ],
  "settings": {
    "typescript.preferences.includePackageJsonAutoImports": "auto",
    "editor.tabSize": 2,
    "editor.insertSpaces": true,
    "files.eol": "\n"
  },
  "extensions": {
    "recommendations": [
      "ms-vscode.vscode-typescript-next",
      "bradlc.vscode-tailwindcss",
      "esbenp.prettier-vscode"
    ]
  }
}
```

## 🧪 **Testing Environment**

### **Playwright Configuration**
```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
  },
});
```

### **Test Scripts**
```json
{
  "scripts": {
    "test": "vitest",
    "test:ui": "vitest --ui",
    "test:coverage": "vitest --coverage",
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui",
    "test:e2e:headed": "playwright test --headed",
    "test:e2e:debug": "playwright test --debug",
    "test:e2e:update-snapshots": "playwright test --update-snapshots"
  }
}
```

### **Unit Testing Framework**

The project includes a comprehensive unit testing framework that runs all unit tests with coverage:

```bash
# Run all unit tests (recommended)
python scripts/simple-unit-tests.py

# Run with options
python scripts/simple-unit-tests.py --python-only
python scripts/simple-unit-tests.py --typescript-only

# Cross-platform scripts
./run-unit-tests.sh                    # Linux/Mac
.\run-unit-tests.ps1                    # Windows
```

**Coverage Reports:**
- **Python Coverage**: `test-results/coverage/python/index.html`
- **TypeScript Coverage**: `test-results/coverage/typescript/index.html`
- **Summary Report**: `test-results/unit-test-report.html`

**Current Coverage**: 272+ unit tests across all services

## 🐳 **Docker Development**

### **Development Docker Compose**
```yaml
# docker-compose.dev.yml
version: '3.8'
services:
  health-dashboard:
    build:
      context: ./services/health-dashboard
      dockerfile: Dockerfile.dev
    ports:
      - "3000:3000"
    volumes:
      - ./services/health-dashboard:/app
      - /app/node_modules
    environment:
      - NODE_ENV=development
      - VITE_API_BASE_URL=http://localhost:8000
      - VITE_WS_URL=ws://localhost:8000/ws
    depends_on:
      - admin-api
      - websocket-ingestion

  admin-api:
    build:
      context: ./services/admin-api
      dockerfile: Dockerfile.dev
    ports:
      - "8000:8000"
    volumes:
      - ./services/admin-api:/app
      - /app/__pycache__
    environment:
      - FLASK_ENV=development
      - FLASK_DEBUG=1

  websocket-ingestion:
    build:
      context: ./services/websocket-ingestion
      dockerfile: Dockerfile.dev
    ports:
      - "8001:8001"
    volumes:
      - ./services/websocket-ingestion:/app
      - /app/__pycache__
    environment:
      - PYTHONPATH=/app
      - LOG_LEVEL=DEBUG
```

### **Start Development Environment**
```bash
# Start all services
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Stop services
docker-compose -f docker-compose.dev.yml down
```

## 📦 **Package Management**

### **Core Dependencies**
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.8.0",
    "chart.js": "^4.2.0",
    "react-chartjs-2": "^5.2.0",
    "chartjs-plugin-zoom": "^2.0.1",
    "chartjs-plugin-annotation": "^3.0.1"
  },
  "devDependencies": {
    "@types/react": "^18.0.0",
    "@types/react-dom": "^18.0.0",
    "@types/react-router-dom": "^5.3.0",
    "@playwright/test": "^1.40.0",
    "@testing-library/react": "^13.4.0",
    "@testing-library/jest-dom": "^5.16.0",
    "vitest": "^0.34.0",
    "vite": "^4.4.0",
    "typescript": "^5.0.0",
    "tailwindcss": "^3.4.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0"
  }
}
```

## 🔍 **Code Quality Tools**

### **ESLint Configuration**
```json
{
  "extends": [
    "eslint:recommended",
    "@typescript-eslint/recommended",
    "plugin:react/recommended",
    "plugin:react-hooks/recommended"
  ],
  "parser": "@typescript-eslint/parser",
  "plugins": ["@typescript-eslint", "react", "react-hooks"],
  "rules": {
    "react/react-in-jsx-scope": "off",
    "react/prop-types": "off",
    "@typescript-eslint/explicit-function-return-type": "off",
    "@typescript-eslint/explicit-module-boundary-types": "off",
    "@typescript-eslint/no-explicit-any": "warn"
  },
  "settings": {
    "react": {
      "version": "detect"
    }
  }
}
```

### **Prettier Configuration**
```json
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 80,
  "tabWidth": 2,
  "useTabs": false
}
```

### **TypeScript Configuration**
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

## 🚀 **Development Workflow**

### **Daily Development Process**
1. **Pull latest changes**: `git pull origin main`
2. **Start development server**: `npm run dev`
3. **Run unit tests**: `python scripts/simple-unit-tests.py`
4. **Make changes** following the implementation guides
5. **Test changes**: `python scripts/simple-unit-tests.py` and `npm run test:e2e`
6. **Commit changes**: `git add . && git commit -m "feat: description"`
7. **Push changes**: `git push origin feature-branch`

### **Feature Development Process**
1. **Create feature branch**: `git checkout -b feature/story-1.1-navigation`
2. **Follow implementation guide** for the specific story
3. **Write tests** as you develop
4. **Run all tests** before committing
5. **Create pull request** when feature is complete
6. **Merge after review** and approval

## 🐛 **Troubleshooting**

### **Common Issues**

#### **Port Already in Use**
```bash
# Kill process on port 3000
npx kill-port 3000

# Or use different port
npm run dev -- --port 3001
```

#### **Node Modules Issues**
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

#### **Playwright Issues**
```bash
# Reinstall Playwright browsers
npx playwright install

# Update Playwright
npm update @playwright/test
```

#### **TypeScript Errors**
```bash
# Restart TypeScript server in VS Code
# Ctrl+Shift+P -> "TypeScript: Restart TS Server"
```

### **Getting Help**
- **Documentation**: Check the implementation guides in `docs/stories/sharded/`
- **Issues**: Create GitHub issues for bugs or questions
- **Discussions**: Use GitHub discussions for general questions
- **Code Review**: Request code reviews for complex changes

## ✅ **Verification Checklist**

Before starting development, verify:

- [ ] Node.js 18+ installed
- [ ] npm 8+ installed
- [ ] Python 3.10+ installed
- [ ] Git configured
- [ ] VS Code with recommended extensions
- [ ] Repository cloned
- [ ] Dependencies installed
- [ ] Environment variables configured
- [ ] Development server starts successfully
- [ ] Unit tests run without errors (`python scripts/simple-unit-tests.py`)
- [ ] E2E tests run without errors
- [ ] Playwright browsers installed

## 🎯 **Next Steps**

1. **Complete this setup** following all steps
2. **Verify everything works** using the checklist
3. **Start with Story 1.1** using the implementation guide
4. **Follow the development workflow** for each story
5. **Ask for help** if you encounter any issues

---

**Ready to start coding? Begin with the Story 1.1 implementation guide!** 🚀


