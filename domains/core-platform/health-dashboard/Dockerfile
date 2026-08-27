# Multi-stage build for Simple Health Dashboard
FROM node:20.20.0-alpine AS deps
WORKDIR /app

# Copy package files
COPY domains/core-platform/health-dashboard/package*.json ./
COPY domains/core-platform/health-dashboard/tsconfig*.json ./
COPY domains/core-platform/health-dashboard/vite.config.ts ./
COPY domains/core-platform/health-dashboard/postcss.config.js ./

# Install dependencies
RUN npm ci

# Build stage
FROM node:20.20.0-alpine AS builder
WORKDIR /app

# Accept build arguments for Vite environment variables.
# There is deliberately no VITE_API_KEY: anything Vite inlines is readable in
# the shipped bundle. nginx injects the credential at request time instead.
ARG VITE_API_BASE_URL
ARG VITE_DATA_API_URL
ARG VITE_WS_INGESTION_URL
ARG VITE_ENVIRONMENT=production

# Copy source code first
COPY domains/core-platform/health-dashboard/ .

# Copy dependencies AFTER source (overrides any stale local node_modules)
COPY --from=deps /app/node_modules ./node_modules

# Set build environment with Vite variables
ENV NODE_ENV=production
ENV VITE_ENVIRONMENT=${VITE_ENVIRONMENT}
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_DATA_API_URL=${VITE_DATA_API_URL}
ENV VITE_WS_INGESTION_URL=${VITE_WS_INGESTION_URL}

# Build the application
RUN npm run build

# Production stage
FROM nginx:stable-alpine AS production

RUN apk add --no-cache --upgrade openssl

# Install curl for health checks and set timezone
RUN apk add --no-cache curl tzdata

# Copy built application
COPY --from=builder /app/dist /usr/share/nginx/html

# nginx config ships as a template so the image entrypoint can substitute
# ${DASHBOARD_API_KEY} at container start. NGINX_ENVSUBST_FILTER restricts
# substitution to that one name — without it envsubst would also eat nginx's
# own runtime variables ($host, $request_uri, ...) and break every proxy_pass.
COPY domains/core-platform/health-dashboard/nginx.conf /etc/nginx/templates/default.conf.template
ENV NGINX_ENVSUBST_FILTER=DASHBOARD_API_KEY

# Create non-root user and set permissions for nginx.
# conf.d must be writable: the entrypoint renders the template into it as appuser.
RUN addgroup -g 1001 -S appgroup && \
    adduser -S appuser -u 1001 -G appgroup && \
    chown -R appuser:appgroup /usr/share/nginx/html && \
    chown -R appuser:appgroup /var/cache/nginx && \
    chown -R appuser:appgroup /var/log/nginx && \
    chown -R appuser:appgroup /etc/nginx/conf.d && \
    chown -R appuser:appgroup /etc/nginx/templates && \
    touch /var/run/nginx.pid && \
    chown appuser:appgroup /var/run/nginx.pid

# Set timezone
ENV TZ=America/Los_Angeles
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Expose port 8080 (non-privileged for non-root user)
EXPOSE 8080

# Switch to non-root user for security
USER appuser

# Health check (uses non-privileged port)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/ || exit 1

# Start nginx as non-root user
CMD ["nginx", "-g", "daemon off;"]