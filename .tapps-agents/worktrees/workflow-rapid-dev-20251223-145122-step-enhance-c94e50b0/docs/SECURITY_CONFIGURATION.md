# Security Configuration Guide

## Overview

This guide explains how to securely configure API keys and sensitive credentials for the HA Ingestor project.

## ⚠️ Important Security Principles

1. **Never commit secrets to version control**
2. **Use environment-specific configuration files**
3. **Store production secrets in secure vaults or CI/CD secrets**
4. **Rotate credentials regularly**
5. **Use minimum required permissions**

## Environment Files

### File Structure

```
infrastructure/
├── env.example          # Template with placeholder values (committed)
└── env.production       # Actual production values (NOT committed, in .gitignore)
```

### Protected Files

The following files are excluded from version control via `.gitignore`:

- `infrastructure/env.production`
- `infrastructure/.env*`
- `.env`
- `.env.local`
- `.env.*.local`

## Configuration Setup

### Local Development

1. **Create your local environment file:**
   ```bash
   cp infrastructure/env.example .env
   ```

2. **Edit `.env` with your development credentials:**
   ```bash
   # Use your development Home Assistant instance
   HOME_ASSISTANT_URL=http://localhost:8123
   HOME_ASSISTANT_TOKEN=your_dev_token_here
   
   # Use a free OpenWeatherMap API key
   WEATHER_API_KEY=your_dev_weather_key_here
   ```

3. **Start development environment:**
   ```bash
   ./scripts/start-dev.sh
   ```

### Production Deployment

#### Option 1: Manual Configuration (Recommended for Small Deployments)

1. **On your production server, create the environment file:**
   ```bash
   cp infrastructure/env.example infrastructure/env.production
   ```

2. **Edit with secure credentials:**
   ```bash
   nano infrastructure/env.production
   ```

3. **Set proper file permissions:**
   ```bash
   chmod 600 infrastructure/env.production
   chown root:root infrastructure/env.production
   ```

#### Option 2: GitHub Secrets (Recommended for CI/CD)

1. **Add secrets to your GitHub repository:**
   - Go to: `Settings` → `Secrets and variables` → `Actions`
   - Click `New repository secret`

2. **Required secrets:**
   ```
   HOME_ASSISTANT_URL
   HOME_ASSISTANT_TOKEN
   NABU_CASA_URL
   NABU_CASA_TOKEN
   WEATHER_API_KEY
   INFLUXDB_USERNAME
   INFLUXDB_PASSWORD
   INFLUXDB_TOKEN
   JWT_SECRET_KEY
   ADMIN_PASSWORD
   ```

3. **Use in GitHub Actions workflow:**
   ```yaml
   # .github/workflows/deploy.yml
   name: Deploy to Production
   
   on:
     push:
       branches: [main]
   
   jobs:
     deploy:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         
         - name: Create production environment file
           run: |
             cat > infrastructure/env.production << EOF
             HOME_ASSISTANT_URL=${{ secrets.HOME_ASSISTANT_URL }}
             HOME_ASSISTANT_TOKEN=${{ secrets.HOME_ASSISTANT_TOKEN }}
             NABU_CASA_URL=${{ secrets.NABU_CASA_URL }}
             NABU_CASA_TOKEN=${{ secrets.NABU_CASA_TOKEN }}
             WEATHER_API_KEY=${{ secrets.WEATHER_API_KEY }}
             INFLUXDB_USERNAME=${{ secrets.INFLUXDB_USERNAME }}
             INFLUXDB_PASSWORD=${{ secrets.INFLUXDB_PASSWORD }}
             INFLUXDB_TOKEN=${{ secrets.INFLUXDB_TOKEN }}
             INFLUXDB_ORG=homeiq
             INFLUXDB_BUCKET=home_assistant_events
             INFLUXDB_URL=http://influxdb:8086
             JWT_SECRET_KEY=${{ secrets.JWT_SECRET_KEY }}
             ADMIN_PASSWORD=${{ secrets.ADMIN_PASSWORD }}
             ENABLE_WEATHER_API=true
             LOG_LEVEL=INFO
             EOF
         
         - name: Deploy
           run: ./scripts/deploy.sh
   ```

#### Option 3: Docker Secrets (Recommended for Docker Swarm)

1. **Create Docker secrets:**
   ```bash
   echo "your_ha_token" | docker secret create ha_token -
   echo "your_weather_key" | docker secret create weather_api_key -
   ```

2. **Update docker-compose.prod.yml:**
   ```yaml
   services:
     websocket-ingestion:
       secrets:
         - ha_token
         - weather_api_key
       environment:
         HOME_ASSISTANT_TOKEN_FILE: /run/secrets/ha_token
         WEATHER_API_KEY_FILE: /run/secrets/weather_api_key
   
   secrets:
     ha_token:
       external: true
     weather_api_key:
       external: true
   ```

#### Option 4: Environment Variables (Cloud Deployments)

For cloud providers (AWS, Azure, GCP), use their secret management services:

**AWS Systems Manager Parameter Store:**
```bash
aws ssm put-parameter \
  --name /homeiq/weather-api-key \
  --value "your_key" \
  --type SecureString

# Retrieve in deployment
WEATHER_API_KEY=$(aws ssm get-parameter \
  --name /homeiq/weather-api-key \
  --with-decryption \
  --query Parameter.Value \
  --output text)
```

**Azure Key Vault:**
```bash
az keyvault secret set \
  --vault-name homeiq-vault \
  --name weather-api-key \
  --value "your_key"
```

## API Key Management

### OpenWeatherMap API Key

1. **Get a free API key:**
   - Visit: https://openweathermap.org/api
   - Sign up for a free account
   - Generate an API key
   - Free tier: 60 calls/minute, 1,000,000 calls/month

2. **Configure the key:**
   ```bash
   WEATHER_API_KEY=your_actual_key_here
   WEATHER_API_URL=https://api.openweathermap.org/data/2.5
   ENABLE_WEATHER_API=true
   ```

### Home Assistant Tokens

1. **Generate a Long-Lived Access Token:**
   - Log into Home Assistant
   - Click on your profile (bottom left)
   - Scroll to "Long-Lived Access Tokens"
   - Click "Create Token"
   - Name it: "HA Ingestor Production"
   - Copy the token immediately (you won't see it again!)

2. **Configure the token:**
   ```bash
   HOME_ASSISTANT_URL=http://your-ha-instance:8123
   HOME_ASSISTANT_TOKEN=your_long_lived_token_here
   ```

### Nabu Casa Integration

1. **Get your Nabu Casa URL:**
   - In Home Assistant, go to Configuration → Home Assistant Cloud
   - Copy your remote URL

2. **Use the same token:**
   ```bash
   NABU_CASA_URL=https://your-instance.ui.nabu.casa
   NABU_CASA_TOKEN=your_long_lived_token_here
   ```

## Security Best Practices

### 1. Credential Rotation

Create a credential rotation schedule:

```bash
# scripts/rotate-credentials.sh
#!/bin/bash

echo "Credential Rotation Checklist:"
echo "1. Generate new Home Assistant token"
echo "2. Update WEATHER_API_KEY if needed"
echo "3. Rotate INFLUXDB_PASSWORD"
echo "4. Update JWT_SECRET_KEY"
echo "5. Update ADMIN_PASSWORD"
echo "6. Update all deployment environments"
echo "7. Test all services"
```

### 2. Environment Validation

The project includes validation scripts:

```bash
# Validate environment configuration
./scripts/setup-env.sh

# Test services with current config
./scripts/test-services.sh
```

### 3. Audit Logging

Monitor credential usage:

```bash
# View logs for authentication events
docker-compose logs websocket-ingestion | grep "auth"

# Check for API key errors
docker-compose logs weather-api | grep "API_KEY"
```

### 4. Least Privilege

Use minimum required permissions:

- **Home Assistant Token**: Only grant access to required entities
- **InfluxDB User**: Read/write only to the specific bucket
- **API Keys**: Use free tier or limited quota keys for development

## Troubleshooting

### Missing API Key

**Error:** `WEATHER_API_KEY not found`

**Solution:**
```bash
# Check if environment file exists
ls -la infrastructure/env.production

# Verify key is set
grep WEATHER_API_KEY infrastructure/env.production

# Restart services to pick up changes
docker-compose restart
```

### Invalid Credentials

**Error:** `401 Unauthorized`

**Solution:**
1. Verify tokens are current and not expired
2. Check for extra whitespace in environment files
3. Regenerate tokens in Home Assistant
4. Update environment files
5. Restart affected services

### Environment File Not Loaded

**Error:** Services using default/placeholder values

**Solution:**
```bash
# Ensure .env file is in project root for development
cp infrastructure/env.example .env

# For production, use env.production
export ENV_FILE=infrastructure/env.production
docker-compose -f docker-compose.prod.yml --env-file $ENV_FILE up -d
```

## Migration Guide

If you previously committed secrets:

### 1. Remove Secrets from Git History

```bash
# Install BFG Repo-Cleaner
brew install bfg  # or download from https://rtyley.github.io/bfg-repo-cleaner/

# Clone a fresh copy
git clone --mirror git@github.com:yourusername/homeiq.git

# Remove sensitive files
bfg --delete-files env.production homeiq.git

# Clean up
cd homeiq.git
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Force push
git push --force
```

### 2. Rotate Compromised Credentials

1. Generate new Home Assistant tokens
2. Get a new Weather API key
3. Update all passwords
4. Update JWT secrets
5. Notify team members

### 3. Update Deployment

1. Update GitHub Secrets
2. Redeploy all environments
3. Verify services are working
4. Monitor logs for issues

## Checklist

Before deploying to production:

- [ ] Removed actual secrets from version control
- [ ] Added sensitive files to `.gitignore`
- [ ] Created `infrastructure/env.production` locally
- [ ] Set proper file permissions (600)
- [ ] Configured GitHub Secrets (if using CI/CD)
- [ ] Tested deployment with new configuration
- [ ] Documented credential locations for team
- [ ] Set up credential rotation schedule
- [ ] Configured monitoring for auth failures
- [ ] Created backup of credentials in secure vault

## Additional Resources

- [Home Assistant Authentication](https://www.home-assistant.io/docs/authentication/)
- [OpenWeatherMap API Documentation](https://openweathermap.org/api)
- [Docker Secrets](https://docs.docker.com/engine/swarm/secrets/)
- [GitHub Actions Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [12-Factor App Config](https://12factor.net/config)

## Support

For questions or issues with security configuration:

1. Check the [Troubleshooting Guide](TROUBLESHOOTING_GUIDE.md)
2. Review logs: `./scripts/view-logs.sh`
3. Create an issue on GitHub (DO NOT include actual secrets!)

