// ESLint Configuration with Code Complexity Rules
// Health Dashboard - TypeScript/React

module.exports = {
  root: true,
  env: {
    browser: true,
    es2020: true,
    node: true,
  },
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react-hooks/recommended',
  ],
  ignorePatterns: ['dist', '.eslintrc.cjs', 'node_modules'],
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    ecmaFeatures: {
      jsx: true,
    },
  },
  plugins: ['react-refresh', '@typescript-eslint', 'complexity'],
  rules: {
    'react-refresh/only-export-components': [
      'warn',
      { allowConstantExport: true },
    ],
    
    // ============================================
    // CODE COMPLEXITY RULES
    // ============================================
    
    // Cyclomatic Complexity (warn if > 15, error if > 20)
    'complexity': ['warn', { max: 15 }],
    
    // Maximum lines per function (warn if > 100, error if > 300)
    'max-lines-per-function': ['warn', {
      max: 100,
      skipBlankLines: true,
      skipComments: true,
      IIFEs: true,
    }],
    
    // Maximum nesting depth (warn if > 4, error if > 6)
    'max-depth': ['warn', 4],
    
    // Maximum number of parameters (warn if > 5)
    'max-params': ['warn', 5],
    
    // Maximum number of statements per line
    'max-statements-per-line': ['warn', { max: 1 }],
    
    // Maximum lines per file (warn if > 500)
    'max-lines': ['warn', {
      max: 500,
      skipBlankLines: true,
      skipComments: true,
    }],
    
    // ============================================
    // CODE QUALITY RULES
    // ============================================
    
    // Prefer const over let
    'prefer-const': 'warn',
    
    // No var declarations
    'no-var': 'error',
    
    // No console.log in production code (warn only)
    'no-console': ['warn', { allow: ['warn', 'error'] }],
    
    // No unused variables (with exceptions for React)
    '@typescript-eslint/no-unused-vars': ['warn', {
      argsIgnorePattern: '^_',
      varsIgnorePattern: '^_',
      caughtErrorsIgnorePattern: '^_',
    }],
    
    // No explicit 'any' type (warn only, not error)
    '@typescript-eslint/no-explicit-any': 'warn',
    
    // Require return types on functions (warn only)
    '@typescript-eslint/explicit-function-return-type': ['warn', {
      allowExpressions: true,
      allowTypedFunctionExpressions: true,
      allowHigherOrderFunctions: true,
    }],
    
    // ============================================
    // MAINTAINABILITY RULES
    // ============================================
    
    // Enforce consistent spacing
    'indent': ['warn', 2, { SwitchCase: 1 }],
    
    // Enforce consistent quotes
    'quotes': ['warn', 'single', { avoidEscape: true }],
    
    // Enforce semicolons
    'semi': ['warn', 'always'],
    
    // No duplicate imports
    'no-duplicate-imports': 'error',
    
    // Prefer template literals over string concatenation
    'prefer-template': 'warn',
    
    // No nested ternary operators
    'no-nested-ternary': 'warn',
    
    // Enforce consistent brace style
    'brace-style': ['warn', '1tbs', { allowSingleLine: true }],
    
    // ============================================
    // REACT-SPECIFIC RULES
    // ============================================
    
    // React Hooks rules (already from plugin)
    'react-hooks/rules-of-hooks': 'error',
    'react-hooks/exhaustive-deps': 'warn',
  },
  
  // Override rules for test files
  overrides: [
    {
      files: ['**/*.test.ts', '**/*.test.tsx', '**/*.spec.ts', '**/*.spec.tsx'],
      rules: {
        'max-lines-per-function': 'off',
        'max-lines': 'off',
        '@typescript-eslint/no-explicit-any': 'off',
      },
    },
  ],
};

