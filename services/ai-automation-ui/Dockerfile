# AI Automation UI - Dockerfile
# Multi-stage build for production-optimized React app

# Stage 1: Dependencies
FROM node:18-alpine AS deps
WORKDIR /app

# Copy dependency files
COPY services/ai-automation-ui/package*.json ./
COPY services/ai-automation-ui/tsconfig*.json ./
COPY services/ai-automation-ui/vite.config.ts ./
COPY services/ai-automation-ui/tailwind.config.js ./
COPY services/ai-automation-ui/postcss.config.js ./

# Install dependencies
RUN --mount=type=cache,target=/root/.npm \
    npm install --prefer-offline --no-audit

# Stage 2: Builder
FROM deps AS builder
WORKDIR /app

# Build arguments for environment variables
ARG VITE_API_URL
ARG VITE_API_KEY

# Set environment variables for build
ENV VITE_API_URL=${VITE_API_URL}
ENV VITE_API_KEY=${VITE_API_KEY}

# Copy dependencies from previous stage
COPY --from=deps /app/node_modules ./node_modules

# Copy source code
COPY services/ai-automation-ui/ .

# Clean any existing build artifacts and cache
RUN rm -rf dist node_modules/.cache .vite 2>/dev/null || true

# Build production bundle
RUN npm run build

# Stage 3: Production
FROM nginx:alpine
LABEL maintainer="HA Ingestor Team"
LABEL description="AI Automation UI - Standalone suggestion management interface"

# Install curl for health checks and tzdata for timezone support
RUN apk add --no-cache curl tzdata

# Copy built files from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY services/ai-automation-ui/nginx.conf /etc/nginx/conf.d/default.conf

# Set timezone to Los Angeles (PST/PDT)
RUN ln -snf /usr/share/zoneinfo/America/Los_Angeles /etc/localtime && \
    echo "America/Los_Angeles" > /etc/timezone

# Expose port 80 (nginx default)
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD curl -f http://localhost/ || exit 1

# Start nginx (nginx handles user permissions internally)
CMD ["nginx", "-g", "daemon off;"]

