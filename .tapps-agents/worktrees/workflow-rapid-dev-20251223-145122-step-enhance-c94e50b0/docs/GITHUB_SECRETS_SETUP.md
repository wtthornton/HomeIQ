# GitHub Secrets Setup Guide

## Overview

This guide walks you through setting up GitHub Secrets for secure CI/CD deployment of the HA Ingestor project.

## Why GitHub Secrets?

GitHub Secrets provide a secure way to store sensitive information like API keys, tokens, and passwords that your CI/CD workflows need without exposing them in your code or repository.

**Benefits:**
- ✅ Encrypted and never exposed in logs
- ✅ Scoped to specific repositories or organizations
- ✅ Easy to rotate and update
- ✅ Integrates seamlessly with GitHub Actions

## Prerequisites

- Repository admin access
- All the credentials you want to store (API keys, tokens, etc.)
- GitHub Actions enabled for your repository

## Step-by-Step Setup

### 1. Navigate to Repository Settings

1. Go to your GitHub repository
2. Click **Settings** (top menu)
3. In the left sidebar, expand **Secrets and variables**
4. Click **Actions**

### 2. Add Required Secrets

Click **New repository secret** for each of the following:

#### Core Secrets (Required)

| Secret Name | Description | How to Get It |
|------------|-------------|---------------|
| `HOME_ASSISTANT_TOKEN` | Home Assistant long-lived access token | [See instructions](#home-assistant-token) |
| `WEATHER_API_KEY` | OpenWeatherMap API key | [Get from OpenWeatherMap](#weather-api-key) |
| `INFLUXDB_PASSWORD` | InfluxDB admin password | [Generate secure password](#secure-passwords) |
| `INFLUXDB_TOKEN` | InfluxDB authentication token | [Generate secure token](#secure-tokens) |
| `JWT_SECRET_KEY` | JWT signing secret | [Generate JWT secret](#jwt-secret) |

#### Optional Secrets

| Secret Name | Description | Default Value |
|------------|-------------|---------------|
| `HOME_ASSISTANT_URL` | Home Assistant URL | `http://homeassistant.local:8123` |
| `NABU_CASA_URL` | Nabu Casa remote URL | (none) |
| `NABU_CASA_TOKEN` | Nabu Casa access token | (none) |
| `INFLUXDB_USERNAME` | InfluxDB username | `admin` |
| `ADMIN_PASSWORD` | Admin API password | [Generate secure password](#secure-passwords) |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `TIMEZONE` | System timezone | `America/Los_Angeles` |

#### Deployment Secrets (for remote deployment)

| Secret Name | Description | When Needed |
|------------|-------------|-------------|
| `PRODUCTION_HOST` | Production server IP/hostname | SSH deployment |
| `PRODUCTION_USER` | SSH username | SSH deployment |
| `SSH_PRIVATE_KEY` | SSH private key | SSH deployment |

#### Docker Hub Secrets (optional)

| Secret Name | Description | When Needed |
|------------|-------------|-------------|
| `DOCKER_HUB_USERNAME` | Docker Hub username | Publishing images |
| `DOCKER_HUB_TOKEN` | Docker Hub access token | Publishing images |

### 3. Getting Required Credentials

#### Home Assistant Token

1. Log into your Home Assistant instance
2. Click your **profile icon** (bottom left corner)
3. Scroll down to **Long-Lived Access Tokens**
4. Click **Create Token**
5. Enter a name: `GitHub Actions - HA Ingestor`
6. Copy the token **immediately** (you won't see it again!)
7. Add it to GitHub Secrets as `HOME_ASSISTANT_TOKEN`

#### Weather API Key

1. Go to [OpenWeatherMap](https://openweathermap.org/)
2. Sign up for a free account
3. Navigate to **API keys** in your account
4. Click **Generate** or copy your existing key
5. Add it to GitHub Secrets as `WEATHER_API_KEY`

**Note:** Free tier provides 60 calls/minute, sufficient for most use cases.

#### Secure Passwords

Generate secure passwords using one of these methods:

**Linux/Mac:**
```bash
openssl rand -base64 32
```

**Python:**
```python
import secrets
print(secrets.token_urlsafe(32))
```

**Online:** Use a password manager like 1Password, Bitwarden, or LastPass

#### Secure Tokens

For InfluxDB token:
```bash
openssl rand -hex 32
```

#### JWT Secret

Generate a secure JWT secret:
```bash
openssl rand -hex 32
```

Or use Python:
```python
import secrets
print(secrets.token_hex(32))
```

### 4. Verify Secrets Are Added

After adding all secrets, you should see them listed (values are hidden):

```
HOME_ASSISTANT_TOKEN      Updated 1 minute ago
WEATHER_API_KEY           Updated 1 minute ago
INFLUXDB_PASSWORD         Updated 1 minute ago
INFLUXDB_TOKEN           Updated 1 minute ago
JWT_SECRET_KEY           Updated 1 minute ago
...
```

## Using Secrets in GitHub Actions

### Basic Usage

The secrets are automatically available in your workflows:

```yaml
- name: Deploy
  env:
    HA_TOKEN: ${{ secrets.HOME_ASSISTANT_TOKEN }}
    WEATHER_KEY: ${{ secrets.WEATHER_API_KEY }}
  run: ./scripts/deploy.sh
```

### Creating Environment File

Example from `.github/workflows/deploy-production.yml.example`:

```yaml
- name: Create production environment file
  run: |
    cat > infrastructure/env.production << 'EOF'
    HOME_ASSISTANT_TOKEN=${{ secrets.HOME_ASSISTANT_TOKEN }}
    WEATHER_API_KEY=${{ secrets.WEATHER_API_KEY }}
    INFLUXDB_PASSWORD=${{ secrets.INFLUXDB_PASSWORD }}
    # ... more variables
    EOF
```

## Security Best Practices

### 1. Principle of Least Privilege

- Only add secrets that are actually needed
- Use environment-specific secrets (dev, staging, prod)
- Limit scope using environment protection rules

### 2. Regular Rotation

Rotate your secrets regularly:

- **Critical secrets** (API keys, tokens): Every 90 days
- **Passwords**: Every 180 days
- **After a breach**: Immediately

### 3. Audit Access

- Review who has access to repository settings
- Monitor GitHub Actions logs for suspicious activity
- Enable branch protection rules

### 4. Never Log Secrets

GitHub automatically masks secrets in logs, but be cautious:

❌ **Bad:**
```yaml
- name: Debug
  run: echo "Token is ${{ secrets.HOME_ASSISTANT_TOKEN }}"
```

✅ **Good:**
```yaml
- name: Verify token exists
  run: |
    if [ -z "${{ secrets.HOME_ASSISTANT_TOKEN }}" ]; then
      echo "Token is missing"
      exit 1
    fi
    echo "Token is present and valid"
```

## Environment Protection

For production deployments, add environment protection rules:

### 1. Create Environment

1. Go to **Settings** → **Environments**
2. Click **New environment**
3. Name it `production`

### 2. Add Protection Rules

Configure protection rules:

- ✅ **Required reviewers**: Add team members who must approve deployments
- ✅ **Wait timer**: Add a delay before deployment (e.g., 5 minutes)
- ✅ **Deployment branches**: Restrict to `main` branch only

### 3. Add Environment Secrets

Add production-specific secrets at the environment level:

1. In the `production` environment settings
2. Click **Add secret**
3. These override repository-level secrets

## Troubleshooting

### Secret Not Found

**Error:** `Secret not found: HOME_ASSISTANT_TOKEN`

**Solutions:**
1. Verify secret name matches exactly (case-sensitive)
2. Check if secret is added at repository level
3. Ensure workflow has permissions to access secrets

### Invalid Secret Value

**Error:** `401 Unauthorized` or similar authentication errors

**Solutions:**
1. Regenerate the credential in the source system
2. Update the secret in GitHub
3. Check for extra whitespace or newlines
4. Verify the secret hasn't expired

### Secrets Not Updating

**Issue:** Changes to secrets don't seem to take effect

**Solutions:**
1. Secrets are read at workflow start - trigger a new run
2. Clear Actions cache: Settings → Actions → Management → Clear cache
3. Verify you updated the correct secret (name is case-sensitive)

### Workflow Permissions

**Error:** `Resource not accessible by integration`

**Solutions:**
1. Go to **Settings** → **Actions** → **General**
2. Under **Workflow permissions**, select:
   - **Read and write permissions**
3. Save changes

## Migration from Committed Secrets

If you previously committed secrets to the repository:

### 1. Add Secrets to GitHub

Follow the steps above to add all secrets to GitHub.

### 2. Update Workflow

Ensure your workflow creates the environment file from secrets:

```yaml
- name: Create environment file
  run: |
    cat > infrastructure/env.production << 'EOF'
    HOME_ASSISTANT_TOKEN=${{ secrets.HOME_ASSISTANT_TOKEN }}
    # ... etc
    EOF
```

### 3. Test Deployment

Run a test deployment to verify all secrets work:

```yaml
workflow_dispatch:  # Enable manual triggering
```

Then go to **Actions** → **Deploy to Production** → **Run workflow**

### 4. Remove From Repository

Once verified working:

```bash
# Remove sensitive file
git rm infrastructure/env.production

# Update .gitignore (already done if you followed the security guide)
git add .gitignore

# Commit
git commit -m "Remove committed secrets, use GitHub Secrets"

# Push
git push origin main
```

### 5. Clean Git History (Optional)

To remove secrets from git history:

```bash
# Use BFG Repo-Cleaner
brew install bfg

# Clone a fresh mirror
git clone --mirror git@github.com:yourusername/homeiq.git

cd homeiq.git

# Remove sensitive files
bfg --delete-files env.production

# Clean up
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Force push (WARNING: This rewrites history!)
git push --force
```

⚠️ **Warning:** This rewrites history. Coordinate with your team first!

## Quick Reference Commands

### Generate Secure Password
```bash
openssl rand -base64 32
```

### Generate Secure Token
```bash
openssl rand -hex 32
```

### List All Secrets (via GitHub CLI)
```bash
gh secret list
```

### Set Secret (via GitHub CLI)
```bash
gh secret set HOME_ASSISTANT_TOKEN
# Paste the value when prompted
```

### Delete Secret (via GitHub CLI)
```bash
gh secret delete HOME_ASSISTANT_TOKEN
```

## Complete Example Workflow

See `.github/workflows/deploy-production.yml.example` for a complete working example that:

- ✅ Validates all required secrets are present
- ✅ Creates environment file from secrets
- ✅ Builds and deploys services
- ✅ Runs health checks
- ✅ Sends notifications on success/failure

## Additional Resources

- [GitHub Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [GitHub Environments](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment)
- [Security Hardening for Actions](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
- [Main Security Configuration Guide](SECURITY_CONFIGURATION.md)

## Need Help?

- Check [Troubleshooting Guide](TROUBLESHOOTING_GUIDE.md)
- Review [Security Configuration Guide](SECURITY_CONFIGURATION.md)
- Create an issue (without including actual secrets!)

---

**Remember:** Keep your secrets secret! Never share them in chat, issues, or commits.

