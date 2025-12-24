# Authentication & Routing Best Practices for React SPAs

**Generated**: October 13, 2025  
**Sources**: Context7 KB (/remix-run/react-router, /react-hook-form/react-hook-form), Security Standards  
**Project**: HA Ingestor Dashboard  
**Stack**: React 18.2, TypeScript 5.2, Vite 5.0

---

## Table of Contents

1. [Authentication Architecture](#authentication-architecture)
2. [React Router Configuration](#react-router-configuration)
3. [Protected Routes Pattern](#protected-routes-pattern)
4. [Login Form Best Practices](#login-form-best-practices)
5. [Token Management](#token-management)
6. [Security Best Practices](#security-best-practices)
7. [UX/Accessibility Guidelines](#uxaccessibility-guidelines)
8. [Implementation Checklist](#implementation-checklist)

---

## Authentication Architecture

### Recommended Pattern: Context + Protected Routes

```typescript
// 1. Auth Context for global state
// 2. Protected Route wrapper for route guards
// 3. Token storage in httpOnly cookies (preferred) or localStorage
// 4. Automatic token refresh
// 5. Redirect handling
```

### Why This Pattern?

- **Centralized Auth State**: Single source of truth for authentication
- **Route Protection**: Declarative route-level access control
- **Security**: Proper token handling prevents XSS attacks
- **UX**: Seamless redirects and session management

---

## React Router Configuration

### 1. Install Dependencies

```bash
npm install react-router-dom@^6.20.0
```

### 2. Basic Router Setup

```typescript
// App.tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Login } from './components/Login';
import { Dashboard } from './components/Dashboard';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<Login />} />
          
          {/* Protected routes */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          
          {/* Catch-all redirect */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
```

### 3. Advanced: Nested Protected Routes

```typescript
// For multiple protected routes
<Routes>
  <Route path="/login" element={<Login />} />
  
  <Route element={<ProtectedRoute />}>
    <Route path="/" element={<Dashboard />} />
    <Route path="/profile" element={<Profile />} />
    <Route path="/settings" element={<Settings />} />
  </Route>
</Routes>
```

---

## Protected Routes Pattern

### Implementation (Based on React Router Best Practices)

```typescript
// components/ProtectedRoute.tsx
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  // Show loading spinner while checking auth status
  if (isLoading) {
    return <div>Loading...</div>;
  }

  // Redirect to login if not authenticated
  // Save the attempted location to redirect back after login
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};
```

### Auth Context Implementation

```typescript
// contexts/AuthContext.tsx
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';

interface User {
  id: string;
  username: string;
  email: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  // Check for existing session on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const token = localStorage.getItem('auth_token');
        if (token) {
          // Validate token with backend
          const response = await fetch('/api/v1/auth/validate', {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          });
          
          if (response.ok) {
            const userData = await response.json();
            setUser(userData);
          } else {
            // Token invalid, clear it
            localStorage.removeItem('auth_token');
          }
        }
      } catch (error) {
        console.error('Auth check failed:', error);
        localStorage.removeItem('auth_token');
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, []);

  const login = async (username: string, password: string) => {
    try {
      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username, password })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Login failed');
      }

      const { token, user: userData } = await response.json();
      
      // Store token
      localStorage.setItem('auth_token', token);
      setUser(userData);
      
      // Redirect to intended page or dashboard
      navigate('/');
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem('auth_token');
    setUser(null);
    navigate('/login');
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
```

---

## Login Form Best Practices

### Using React Hook Form (Recommended)

```typescript
// components/Login.tsx
import { useForm } from 'react-hook-form';
import { useAuth } from '../contexts/AuthContext';
import { useLocation, Navigate } from 'react-router-dom';
import { useState } from 'react';

interface LoginFormData {
  username: string;
  password: string;
}

export const Login: React.FC = () => {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<LoginFormData>();
  const { login, isAuthenticated } = useAuth();
  const location = useLocation();
  const [loginError, setLoginError] = useState<string>('');

  // Redirect if already authenticated
  const from = (location.state as any)?.from?.pathname || '/';
  if (isAuthenticated) {
    return <Navigate to={from} replace />;
  }

  const onSubmit = async (data: LoginFormData) => {
    try {
      setLoginError('');
      await login(data.username, data.password);
    } catch (error) {
      setLoginError(error instanceof Error ? error.message : 'Login failed');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100 dark:bg-gray-900">
      <div className="max-w-md w-full space-y-8 p-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg">
        <div>
          <h2 className="text-center text-3xl font-bold text-gray-900 dark:text-white">
            🏠 HA Ingestor Dashboard
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600 dark:text-gray-400">
            Sign in to your account
          </p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="mt-8 space-y-6" noValidate>
          {loginError && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded" role="alert">
              <span className="block sm:inline">{loginError}</span>
            </div>
          )}

          <div className="space-y-4">
            {/* Username Field */}
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Username
              </label>
              <input
                id="username"
                type="text"
                autoComplete="username"
                {...register('username', {
                  required: 'Username is required',
                  minLength: {
                    value: 3,
                    message: 'Username must be at least 3 characters'
                  }
                })}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                aria-invalid={errors.username ? 'true' : 'false'}
                aria-describedby={errors.username ? 'username-error' : undefined}
              />
              {errors.username && (
                <p id="username-error" className="mt-1 text-sm text-red-600 dark:text-red-400" role="alert">
                  {errors.username.message}
                </p>
              )}
            </div>

            {/* Password Field */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                {...register('password', {
                  required: 'Password is required',
                  minLength: {
                    value: 6,
                    message: 'Password must be at least 6 characters'
                  }
                })}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                aria-invalid={errors.password ? 'true' : 'false'}
                aria-describedby={errors.password ? 'password-error' : undefined}
              />
              {errors.password && (
                <p id="password-error" className="mt-1 text-sm text-red-600 dark:text-red-400" role="alert">
                  {errors.password.message}
                </p>
              )}
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isSubmitting ? 'Signing in...' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  );
};
```

### Key Form Features:

1. **React Hook Form Integration**: Performant, minimal re-renders
2. **Validation**: Client-side validation with clear error messages
3. **Accessibility**: 
   - Proper `label` associations
   - ARIA attributes (`aria-invalid`, `aria-describedby`)
   - Error announcements with `role="alert"`
4. **UX**: 
   - Loading states
   - Error feedback
   - Disabled state during submission
5. **Security**: `noValidate` to disable browser validation (use custom)
6. **Autocomplete**: Proper `autoComplete` attributes for password managers

---

## Token Management

### Storage Options (Security Trade-offs)

| Method | Security | XSS Protection | CSRF Protection | Best For |
|--------|----------|----------------|-----------------|----------|
| **HttpOnly Cookies** | ⭐⭐⭐⭐⭐ | Yes | Requires CSRF token | Production |
| **localStorage** | ⭐⭐⭐ | No | Yes | Development, SPAs |
| **sessionStorage** | ⭐⭐⭐⭐ | No | Yes | Temporary sessions |
| **Memory only** | ⭐⭐⭐⭐⭐ | Yes | Yes | High security (no refresh) |

### Recommended: localStorage for SPA (Development)

```typescript
// utils/tokenStorage.ts

const TOKEN_KEY = 'auth_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

export const tokenStorage = {
  getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  },

  setToken(token: string): void {
    localStorage.setItem(TOKEN_KEY, token);
  },

  getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  },

  setRefreshToken(token: string): void {
    localStorage.setItem(REFRESH_TOKEN_KEY, token);
  },

  clearTokens(): void {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  }
};
```

### API Client with Token Injection

```typescript
// services/api.ts
import { tokenStorage } from '../utils/tokenStorage';

export const apiClient = {
  async request(url: string, options: RequestInit = {}) {
    const token = tokenStorage.getToken();
    
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` }),
      ...options.headers
    };

    const response = await fetch(url, {
      ...options,
      headers
    });

    // Handle 401 Unauthorized
    if (response.status === 401) {
      // Token expired, clear and redirect to login
      tokenStorage.clearTokens();
      window.location.href = '/login';
      throw new Error('Session expired');
    }

    return response;
  },

  async get(url: string) {
    return this.request(url);
  },

  async post(url: string, data: any) {
    return this.request(url, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }
};
```

---

## Security Best Practices

### 1. Input Validation

```typescript
// Both client AND server-side validation required

// Client validation (React Hook Form)
{
  ...register('username', {
    required: 'Username is required',
    minLength: { value: 3, message: 'Min 3 characters' },
    maxLength: { value: 50, message: 'Max 50 characters' },
    pattern: {
      value: /^[a-zA-Z0-9_]+$/,
      message: 'Only letters, numbers, and underscores'
    }
  })
}
```

### 2. Password Security

```typescript
// Minimum requirements
const passwordRules = {
  required: 'Password is required',
  minLength: {
    value: 8,
    message: 'Password must be at least 8 characters'
  },
  pattern: {
    value: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
    message: 'Must contain uppercase, lowercase, and number'
  }
};

// NEVER log passwords
// NEVER store passwords in localStorage
// ALWAYS hash passwords on server (bcrypt, argon2)
```

### 3. CSRF Protection

```typescript
// For state-changing operations, include CSRF token
const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

fetch('/api/v1/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRF-Token': csrfToken
  },
  body: JSON.stringify(credentials)
});
```

### 4. Rate Limiting

Implement on backend:
- Maximum 5 login attempts per IP per 15 minutes
- Exponential backoff
- Account lockout after failed attempts

### 5. HTTPS Only

```typescript
// Ensure all auth requests use HTTPS in production
if (process.env.NODE_ENV === 'production' && !window.location.protocol.startsWith('https')) {
  console.error('Authentication requires HTTPS');
}
```

---

## UX/Accessibility Guidelines

### 1. Loading States

```typescript
// Show spinner during auth check
if (isLoading) {
  return (
    <div role="status" aria-live="polite" className="flex items-center justify-center min-h-screen">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
      <span className="sr-only">Loading...</span>
    </div>
  );
}
```

### 2. Error Messages

```typescript
// Clear, actionable error messages
const errorMessages = {
  'invalid_credentials': 'Invalid username or password. Please try again.',
  'account_locked': 'Your account has been locked. Contact support.',
  'network_error': 'Unable to connect. Please check your internet connection.',
  'server_error': 'Something went wrong. Please try again later.'
};
```

### 3. Keyboard Navigation

- Tab order: Username → Password → Submit
- Enter key submits form
- Escape key clears fields (optional)
- Focus management on error

### 4. Screen Reader Support

```typescript
// Announce errors to screen readers
<div role="alert" aria-live="assertive">
  {error && <p>{error}</p>}
</div>

// Label all form fields properly
<label htmlFor="username">Username</label>
<input id="username" aria-required="true" />
```

### 5. Remember Me (Optional)

```typescript
// Store username only (not password!)
const rememberMe = watch('rememberMe');

if (rememberMe) {
  localStorage.setItem('remembered_username', username);
} else {
  localStorage.removeItem('remembered_username');
}
```

---

## Implementation Checklist

### Phase 1: Core Authentication (P0)

- [ ] Install react-router-dom
- [ ] Create AuthContext with login/logout
- [ ] Create ProtectedRoute component
- [ ] Configure router in App.tsx
- [ ] Create Login page component
- [ ] Implement token storage utilities
- [ ] Add API client with token injection
- [ ] Add logout button to dashboard

### Phase 2: Security & Validation (P1)

- [ ] Add React Hook Form to login
- [ ] Implement client-side validation
- [ ] Add error handling and display
- [ ] Implement loading states
- [ ] Add 401 redirect handling
- [ ] Test protected route redirects
- [ ] Verify token persistence across page refreshes

### Phase 3: UX & Polish (P2)

- [ ] Add ARIA labels to form fields
- [ ] Implement keyboard navigation
- [ ] Add loading spinners
- [ ] Improve error messages
- [ ] Add "Remember me" functionality
- [ ] Test with screen readers
- [ ] Add password visibility toggle

### Phase 4: Backend Integration (P1)

- [ ] Create /api/v1/auth/login endpoint
- [ ] Create /api/v1/auth/validate endpoint
- [ ] Create /api/v1/auth/logout endpoint
- [ ] Implement JWT token generation
- [ ] Add password hashing (bcrypt)
- [ ] Implement rate limiting
- [ ] Add CORS configuration
- [ ] Test end-to-end flow

---

## Testing Strategy

### Unit Tests

```typescript
// Login.test.tsx
describe('Login Component', () => {
  it('displays validation errors for empty fields', async () => {
    render(<Login />);
    fireEvent.click(screen.getByText('Sign in'));
    expect(await screen.findByText('Username is required')).toBeInTheDocument();
  });

  it('calls login API on form submission', async () => {
    const mockLogin = jest.fn();
    render(<Login />);
    // ... test implementation
  });
});
```

### E2E Tests (Playwright)

```typescript
// login.spec.ts
test('successful login redirects to dashboard', async ({ page }) => {
  await page.goto('http://localhost:3000/login');
  await page.fill('input[name="username"]', 'testuser');
  await page.fill('input[name="password"]', 'password123');
  await page.click('button[type="submit"]');
  await expect(page).toHaveURL('http://localhost:3000/');
});
```

---

## References

- React Router v7 Documentation: `/remix-run/react-router`
- React Hook Form: `/react-hook-form/react-hook-form`
- OWASP Authentication Cheat Sheet
- WCAG 2.1 AA Guidelines

---

**Last Updated**: October 13, 2025  
**Maintained By**: BMad Master Agent  
**Cache Status**: Active

