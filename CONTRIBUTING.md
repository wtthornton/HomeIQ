# Contributing to HomeIQ

Thank you for your interest in contributing to HomeIQ! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Pull Request Process](#pull-request-process)
- [Code Quality Standards](#code-quality-standards)
- [Testing Requirements](#testing-requirements)
- [Commit Message Conventions](#commit-message-conventions)
- [Documentation Guidelines](#documentation-guidelines)
- [Getting Help](#getting-help)

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inspiring community for all. Please be respectful and constructive in all interactions.

### Expected Behavior

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on what is best for the community
- Show empathy towards other community members

### Unacceptable Behavior

- Harassment, discrimination, or offensive comments
- Trolling, insulting, or derogatory remarks
- Publishing others' private information
- Other conduct which could reasonably be considered inappropriate

---

## Getting Started

### Prerequisites

Before you begin, ensure you have:

- **Docker** 20.10+ and **Docker Compose** 2.0+
- **Python** 3.11+ (for local development)
- **Node.js** 20+ (for frontend development)
- **Git** for version control
- A **Home Assistant** instance for testing

### Development Environment Setup

1. **Fork and Clone**
   ```bash
   # Fork the repository on GitHub
   # Clone your fork
   git clone https://github.com/YOUR_USERNAME/HomeIQ.git
   cd HomeIQ

   # Add upstream remote
   git remote add upstream https://github.com/wtthornton/HomeIQ.git
   ```

2. **Set Up Environment**
   ```bash
   # Copy environment template
   cp infrastructure/env.example infrastructure/.env

   # Configure your Home Assistant connection
   # Edit infrastructure/.env with your HA details
   nano infrastructure/.env
   ```

3. **Start Development Environment**
   ```bash
   # Start all services
   docker compose up -d

   # Verify deployment
   ./scripts/verify-deployment.sh
   ```

4. **Access Services**
   - Health Dashboard: http://localhost:3000
   - AI Automation UI: http://localhost:3001
   - API Documentation: http://localhost:8003/docs

---

## Development Workflow

### 1. Create a Feature Branch

```bash
# Update your fork
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/amazing-feature
```

### 2. Make Your Changes

- Write clean, readable code
- Follow existing code style
- Add comments for complex logic
- Update documentation as needed

### 3. Test Your Changes

```bash
# For Python services
cd services/service-name
pytest tests/

# For frontend
cd services/health-dashboard
npm test
```

### 4. Commit Your Changes

```bash
# Stage your changes
git add .

# Commit with descriptive message
git commit -m "feat: add amazing feature"
```

See [Commit Message Conventions](#commit-message-conventions) below.

### 5. Push and Create Pull Request

```bash
# Push to your fork
git push origin feature/amazing-feature

# Create Pull Request on GitHub
```

---

## Pull Request Process

### Before Submitting

- [ ] Code follows project style guidelines
- [ ] All tests pass
- [ ] Documentation updated (if applicable)
- [ ] No console errors or warnings
- [ ] Commit messages follow conventions
- [ ] PR description clearly explains changes

### PR Title Format

Use conventional commit format:
```
<type>(<scope>): <short summary>

Examples:
feat(ai-automation): add new synergy detection algorithm
fix(websocket): resolve connection retry logic
docs(readme): update installation instructions
```

### PR Description Template

```markdown
## Description
Brief description of what this PR does.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Documentation update

## How Has This Been Tested?
Describe the tests you ran and how to reproduce them.

## Checklist
- [ ] My code follows the code style of this project
- [ ] My change requires a change to the documentation
- [ ] I have updated the documentation accordingly
- [ ] I have added tests to cover my changes
- [ ] All new and existing tests passed
```

### Review Process

1. **Automated Checks** - CI/CD will run automated tests
2. **Code Review** - Maintainers will review your code
3. **Feedback** - Address any requested changes
4. **Approval** - Once approved, your PR will be merged

---

## Code Quality Standards

### Python Code Standards

Follow PEP 8 style guide:

```python
"""
Module docstring explaining purpose
"""

from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)


class ExampleService:
    """
    Class docstring explaining the service
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the service

        Args:
            config: Configuration dictionary

        Raises:
            ValueError: If configuration is invalid
        """
        self.config = config

    def process_data(self, data: List[Dict]) -> Optional[Dict]:
        """
        Process data and return results

        Args:
            data: List of data dictionaries to process

        Returns:
            Processed results or None if processing failed

        Raises:
            ProcessingError: If data processing fails
        """
        try:
            # Process data
            result = self._internal_process(data)
            return result
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            return None
```

**Key Points:**
- Use type hints for all function parameters and return values
- Add docstrings to all classes and functions
- Use descriptive variable names
- Keep functions focused and small (<50 lines)
- Handle errors gracefully with try/except
- Use logging instead of print statements

### TypeScript/React Code Standards

Follow Airbnb JavaScript Style Guide:

```typescript
/**
 * Example React component with TypeScript
 */
import React, { useState, useEffect } from 'react';

interface ExampleProps {
  /** Service name to display */
  serviceName: string;
  /** Optional callback on status change */
  onStatusChange?: (status: string) => void;
}

/**
 * Example component that displays service status
 */
export const ExampleComponent: React.FC<ExampleProps> = ({
  serviceName,
  onStatusChange
}) => {
  const [status, setStatus] = useState<string>('loading');

  useEffect(() => {
    // Fetch status
    fetchStatus();
  }, [serviceName]);

  const fetchStatus = async () => {
    try {
      const response = await fetch(`/api/status/${serviceName}`);
      const data = await response.json();
      setStatus(data.status);
      onStatusChange?.(data.status);
    } catch (error) {
      console.error('Failed to fetch status:', error);
      setStatus('error');
    }
  };

  return (
    <div className="example-component">
      <h2>{serviceName}</h2>
      <p>Status: {status}</p>
    </div>
  );
};
```

**Key Points:**
- Use TypeScript for type safety
- Add JSDoc comments to interfaces and functions
- Use functional components with hooks
- Handle loading and error states
- Use meaningful component and prop names

### Code Formatting

```bash
# Python
black .
isort .
flake8 .

# TypeScript/JavaScript
npm run format  # Prettier
npm run lint    # ESLint
```

---

## Testing Requirements

### Python Services

**Unit Tests (Required)**
```python
import pytest
from src.example_service import ExampleService

def test_process_data():
    """Test data processing"""
    service = ExampleService({'key': 'value'})
    data = [{'id': 1, 'value': 'test'}]

    result = service.process_data(data)

    assert result is not None
    assert result['count'] == 1
```

**Test Coverage Target:** 80%+

```bash
# Run tests with coverage
pytest --cov=src tests/
```

### Frontend Testing

**Component Tests (Required)**
```typescript
import { render, screen } from '@testing-library/react';
import { ExampleComponent } from './ExampleComponent';

describe('ExampleComponent', () => {
  it('renders service name', () => {
    render(<ExampleComponent serviceName="test-service" />);
    expect(screen.getByText('test-service')).toBeInTheDocument();
  });

  it('displays status', async () => {
    render(<ExampleComponent serviceName="test-service" />);
    // Add assertions
  });
});
```

**Test Coverage Target:** 70%+

```bash
# Run tests
npm test

# Run with coverage
npm run test:coverage
```

### Integration Tests

Not currently required but encouraged for complex features.

---

## Commit Message Conventions

Follow **Conventional Commits** specification:

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- **feat:** New feature
- **fix:** Bug fix
- **docs:** Documentation changes
- **style:** Code style changes (formatting, etc.)
- **refactor:** Code refactoring
- **test:** Adding or updating tests
- **chore:** Maintenance tasks
- **perf:** Performance improvements
- **ci:** CI/CD changes

### Scopes

Use service or component name:
- `ai-automation`
- `websocket`
- `health-dashboard`
- `data-api`
- `docs`
- `readme`

### Examples

```bash
# Feature
git commit -m "feat(ai-automation): add multi-hop synergy detection"

# Bug fix
git commit -m "fix(websocket): resolve infinite retry loop on network error"

# Documentation
git commit -m "docs(readme): update installation instructions for Docker"

# With body
git commit -m "feat(data-api): add device utilization endpoint

- Add /api/device-utilization endpoint
- Calculate feature usage percentage
- Include historical comparison"

# Breaking change
git commit -m "feat(api)!: change response format for /api/suggestions

BREAKING CHANGE: Response now returns {data, meta} instead of flat array"
```

---

## Documentation Guidelines

### When to Update Documentation

Update documentation when you:
- Add a new feature
- Change API endpoints
- Modify configuration options
- Fix a bug that affects usage
- Change deployment process

### Documentation Files to Update

- **README.md** - For major features or changes
- **Service README** - For service-specific changes
- **API Documentation** - For API changes
- **Architecture Docs** - For architectural changes
- **CHANGELOG.md** - For all user-facing changes

### Documentation Style

- Use clear, concise language
- Include code examples
- Add expected outputs
- Use proper markdown formatting
- Keep paragraphs short (2-4 sentences)
- Use headings for navigation

### Example Documentation Update

```markdown
## New Feature: Multi-Hop Synergy Detection

### Overview
HomeIQ now detects multi-hop device relationships (A → B → C).

### Usage
```bash
# Detect 3-level chains
curl http://localhost:8024/api/synergies?synergy_depth=3
```

### Response
```json
{
  "synergies": [
    {
      "devices": ["door_sensor", "smart_lock", "alarm"],
      "depth": 3,
      "confidence": 0.95
    }
  ]
}
```
```

---

## Getting Help

### Questions?

- **GitHub Discussions** - For general questions and discussions
- **GitHub Issues** - For bug reports and feature requests
- **Project Wiki** - For additional documentation

### Resources

- [Architecture Documentation](docs/architecture/)
- [API Reference](docs/api/API_REFERENCE.md)
- [Development Environment Setup](docs/development-environment-setup.md)
- [Troubleshooting Guide](docs/TROUBLESHOOTING_GUIDE.md)

---

## License

By contributing to HomeIQ, you agree that your contributions will be licensed under the ISC License.

---

## Recognition

Contributors will be recognized in:
- Project README
- Release notes
- GitHub contributors page

Thank you for contributing to HomeIQ! 🎉
