# Multi-stage build for Simple Health Dashboard
FROM node:18-alpine AS deps
WORKDIR /app

# Copy package files
COPY package*.json ./
COPY tsconfig*.json ./
COPY vite.config.ts ./
COPY tailwind.config.js ./
COPY postcss.config.js ./

# Install dependencies with cache mount and prefer offline
RUN --mount=type=cache,target=/root/.npm \
    npm ci --prefer-offline

# Build stage
FROM node:18-alpine AS builder
WORKDIR /app

# Accept build arguments for Vite environment variables
ARG VITE_API_BASE_URL
ARG VITE_API_KEY
ARG VITE_DATA_API_URL
ARG VITE_WS_URL
ARG VITE_ENVIRONMENT=production

# Copy dependencies
COPY --from=deps /app/node_modules ./node_modules

# Copy source code
COPY . .

# Set build environment with Vite variables
ENV NODE_ENV=production
ENV VITE_ENVIRONMENT=${VITE_ENVIRONMENT}
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_API_KEY=${VITE_API_KEY}
ENV VITE_DATA_API_URL=${VITE_DATA_API_URL}
ENV VITE_WS_URL=${VITE_WS_URL}

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine AS production

# Install curl for health checks and set timezone
RUN apk add --no-cache curl tzdata

# Copy built application
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Create non-root user for file ownership
RUN addgroup -g 1001 -S appgroup && \
    adduser -S appuser -u 1001 -G appgroup

# Set ownership of web files to non-root user
RUN chown -R appuser:appgroup /usr/share/nginx/html

# Set timezone
ENV TZ=America/Los_Angeles
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]