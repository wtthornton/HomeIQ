# docker-bake.hcl — Docker Buildx Bake definition for HomeIQ
# Build all services:  docker buildx bake full
# Build one domain:    docker buildx bake core-platform
# Build one service:   docker buildx bake data-api

# ──────────────────────────────────────────────
# Variables
# ──────────────────────────────────────────────

variable "PYTHON_VERSION" {
  default = "3.11-slim"
}

variable "NODE_VERSION" {
  default = "20-alpine"
}

# ──────────────────────────────────────────────
# Group 1: core-platform
# influxdb is image-only (no build target)
# postgres is image-only (no build target) — uses postgres:17-alpine
# ──────────────────────────────────────────────

target "data-api" {
  context    = "."
  dockerfile = "domains/core-platform/data-api/Dockerfile"
  tags       = ["homeiq/data-api:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "websocket-ingestion" {
  context    = "."
  dockerfile = "domains/core-platform/websocket-ingestion/Dockerfile"
  tags       = ["homeiq/websocket-ingestion:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "admin-api" {
  context    = "."
  dockerfile = "domains/core-platform/admin-api/Dockerfile"
  tags       = ["homeiq/admin-api:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "health-dashboard" {
  context    = "."
  dockerfile = "domains/core-platform/health-dashboard/Dockerfile"
  tags       = ["homeiq/health-dashboard:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "data-retention" {
  context    = "."
  dockerfile = "domains/core-platform/data-retention/Dockerfile"
  tags       = ["homeiq/data-retention:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "ha-simulator" {
  context    = "."
  dockerfile = "domains/core-platform/ha-simulator/Dockerfile"
  tags       = ["homeiq/ha-simulator:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

group "core-platform" {
  targets = [
    "data-api",
    "websocket-ingestion",
    "admin-api",
    "health-dashboard",
    "data-retention",
    "ha-simulator",
  ]
}

# ──────────────────────────────────────────────
# Group 2: data-collectors
# ──────────────────────────────────────────────

target "weather-api" {
  context    = "."
  dockerfile = "domains/data-collectors/weather-api/Dockerfile"
  tags       = ["homeiq/weather-api:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "smart-meter-service" {
  context    = "."
  dockerfile = "domains/data-collectors/smart-meter-service/Dockerfile"
  tags       = ["homeiq/smart-meter-service:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "sports-api" {
  context    = "."
  dockerfile = "domains/data-collectors/sports-api/Dockerfile"
  tags       = ["homeiq/sports-api:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "air-quality-service" {
  context    = "."
  dockerfile = "domains/data-collectors/air-quality-service/Dockerfile"
  tags       = ["homeiq/air-quality-service:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "carbon-intensity-service" {
  context    = "."
  dockerfile = "domains/data-collectors/carbon-intensity-service/Dockerfile"
  tags       = ["homeiq/carbon-intensity-service:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "electricity-pricing-service" {
  context    = "."
  dockerfile = "domains/data-collectors/electricity-pricing-service/Dockerfile"
  tags       = ["homeiq/electricity-pricing-service:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "calendar-service" {
  context    = "."
  dockerfile = "domains/data-collectors/calendar-service/Dockerfile"
  tags       = ["homeiq/calendar-service:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "log-aggregator" {
  context    = "."
  dockerfile = "domains/data-collectors/log-aggregator/Dockerfile"
  tags       = ["homeiq/log-aggregator:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

group "data-collectors" {
  targets = [
    "weather-api",
    "smart-meter-service",
    "sports-api",
    "air-quality-service",
    "carbon-intensity-service",
    "electricity-pricing-service",
    "calendar-service",
    "log-aggregator",
  ]
}

# ──────────────────────────────────────────────
# Group 3: ml-engine
# ner-service and openai-service now have proper Dockerfiles
# ──────────────────────────────────────────────

target "openvino-service" {
  context    = "."
  dockerfile = "domains/ml-engine/openvino-service/Dockerfile"
  tags       = ["homeiq/openvino-service:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "ml-service" {
  context    = "."
  dockerfile = "domains/ml-engine/ml-service/Dockerfile"
  tags       = ["homeiq/ml-service:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "ner-service" {
  context    = "."
  dockerfile = "domains/ml-engine/ner-service/Dockerfile"
  tags       = ["homeiq/ner-service:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "openai-service" {
  context    = "."
  dockerfile = "domains/ml-engine/openai-service/Dockerfile"
  tags       = ["homeiq/openai-service:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "rag-service" {
  context    = "."
  dockerfile = "domains/ml-engine/rag-service/Dockerfile"
  tags       = ["homeiq/rag-service:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "ai-core-service" {
  context    = "."
  dockerfile = "domains/ml-engine/ai-core-service/Dockerfile"
  tags       = ["homeiq/ai-core-service:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "ai-training-service" {
  context    = "."
  dockerfile = "domains/ml-engine/ai-training-service/Dockerfile"
  tags       = ["homeiq/ai-training-service:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "device-intelligence-service" {
  context    = "."
  dockerfile = "domains/ml-engine/device-intelligence-service/Dockerfile"
  tags       = ["homeiq/device-intelligence-service:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "model-prep" {
  context    = "."
  dockerfile = "domains/ml-engine/model-prep/Dockerfile"
  tags       = ["homeiq/model-prep:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

group "ml-engine" {
  targets = [
    "openvino-service",
    "ml-service",
    "ner-service",
    "openai-service",
    "rag-service",
    "ai-core-service",
    "ai-training-service",
    "device-intelligence-service",
    "model-prep",
  ]
}

# ──────────────────────────────────────────────
# Group 4: automation-core
# ──────────────────────────────────────────────

target "ha-ai-agent-service" {
  context    = "."
  dockerfile = "domains/automation-core/ha-ai-agent-service/Dockerfile"
  tags       = ["homeiq/ha-ai-agent-service:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "ai-automation-service-new" {
  context    = "."
  dockerfile = "domains/automation-core/ai-automation-service-new/Dockerfile"
  tags       = ["homeiq/ai-automation-service-new:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "ai-query-service" {
  context    = "."
  dockerfile = "domains/automation-core/ai-query-service/Dockerfile"
  tags       = ["homeiq/ai-query-service:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "automation-linter" {
  context    = "."
  dockerfile = "domains/automation-core/automation-linter/Dockerfile"
  tags       = ["homeiq/automation-linter:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "yaml-validation-service" {
  context    = "."
  dockerfile = "domains/automation-core/yaml-validation-service/Dockerfile"
  tags       = ["homeiq/yaml-validation-service:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "ai-code-executor" {
  context    = "."
  dockerfile = "domains/automation-core/ai-code-executor/Dockerfile"
  tags       = ["homeiq/ai-code-executor:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "automation-trace-service" {
  context    = "."
  dockerfile = "domains/automation-core/automation-trace-service/Dockerfile"
  tags       = ["homeiq/automation-trace-service:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

group "automation-core" {
  targets = [
    "ha-ai-agent-service",
    "ai-automation-service-new",
    "ai-query-service",
    "automation-linter",
    "yaml-validation-service",
    "ai-code-executor",
    "automation-trace-service",
  ]
}

# ──────────────────────────────────────────────
# Group 5: blueprints
# blueprint-index and rule-recommendation-ml have local context
# ──────────────────────────────────────────────

target "blueprint-index" {
  context    = "."
  dockerfile = "domains/blueprints/blueprint-index/Dockerfile"
  tags       = ["homeiq/blueprint-index:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "blueprint-suggestion-service" {
  context    = "."
  dockerfile = "domains/blueprints/blueprint-suggestion-service/Dockerfile"
  tags       = ["homeiq/blueprint-suggestion-service:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "rule-recommendation-ml" {
  context    = "."
  dockerfile = "domains/blueprints/rule-recommendation-ml/Dockerfile"
  tags       = ["homeiq/rule-recommendation-ml:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "automation-miner" {
  context    = "."
  dockerfile = "domains/blueprints/automation-miner/Dockerfile"
  tags       = ["homeiq/automation-miner:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

group "blueprints" {
  targets = [
    "blueprint-index",
    "blueprint-suggestion-service",
    "rule-recommendation-ml",
    "automation-miner",
  ]
}

# ──────────────────────────────────────────────
# Group 6: energy-analytics
# energy-forecasting has local context
# ──────────────────────────────────────────────

target "energy-correlator" {
  context    = "."
  dockerfile = "domains/energy-analytics/energy-correlator/Dockerfile"
  tags       = ["homeiq/energy-correlator:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "energy-forecasting" {
  context    = "."
  dockerfile = "domains/energy-analytics/energy-forecasting/Dockerfile"
  tags       = ["homeiq/energy-forecasting:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "proactive-agent-service" {
  context    = "."
  dockerfile = "domains/energy-analytics/proactive-agent-service/Dockerfile"
  tags       = ["homeiq/proactive-agent-service:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

group "energy-analytics" {
  targets = [
    "energy-correlator",
    "energy-forecasting",
    "proactive-agent-service",
  ]
}

# ──────────────────────────────────────────────
# Group 7: device-management
# activity-recognition and ha-setup-service have local context
# ──────────────────────────────────────────────

target "device-health-monitor" {
  context    = "."
  dockerfile = "domains/device-management/device-health-monitor/Dockerfile"
  tags       = ["homeiq/device-health-monitor:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "device-context-classifier" {
  context    = "."
  dockerfile = "domains/device-management/device-context-classifier/Dockerfile"
  tags       = ["homeiq/device-context-classifier:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "device-setup-assistant" {
  context    = "."
  dockerfile = "domains/device-management/device-setup-assistant/Dockerfile"
  tags       = ["homeiq/device-setup-assistant:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "device-database-client" {
  context    = "."
  dockerfile = "domains/device-management/device-database-client/Dockerfile"
  tags       = ["homeiq/device-database-client:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "device-recommender" {
  context    = "."
  dockerfile = "domains/device-management/device-recommender/Dockerfile"
  tags       = ["homeiq/device-recommender:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "activity-recognition" {
  context    = "."
  dockerfile = "domains/device-management/activity-recognition/Dockerfile"
  tags       = ["homeiq/activity-recognition:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "activity-writer" {
  context    = "."
  dockerfile = "domains/device-management/activity-writer/Dockerfile"
  tags       = ["homeiq/activity-writer:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "ha-setup-service" {
  context    = "."
  dockerfile = "domains/device-management/ha-setup-service/Dockerfile"
  tags       = ["homeiq/ha-setup-service:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

group "device-management" {
  targets = [
    "device-health-monitor",
    "device-context-classifier",
    "device-setup-assistant",
    "device-database-client",
    "device-recommender",
    "activity-recognition",
    "activity-writer",
    "ha-setup-service",
  ]
}

# ──────────────────────────────────────────────
# Group 8: pattern-analysis
# ──────────────────────────────────────────────

target "ai-pattern-service" {
  context    = "."
  dockerfile = "domains/pattern-analysis/ai-pattern-service/Dockerfile"
  tags       = ["homeiq/ai-pattern-service:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "api-automation-edge" {
  context    = "."
  dockerfile = "domains/pattern-analysis/api-automation-edge/Dockerfile"
  tags       = ["homeiq/api-automation-edge:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

group "pattern-analysis" {
  targets = [
    "ai-pattern-service",
    "api-automation-edge",
  ]
}

# ──────────────────────────────────────────────
# Group 9: frontends
# jaeger is image-only (no build target)
# ──────────────────────────────────────────────

target "observability-dashboard" {
  context    = "."
  dockerfile = "domains/frontends/observability-dashboard/Dockerfile"
  tags       = ["homeiq/observability-dashboard:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

target "ai-automation-ui" {
  context    = "."
  dockerfile = "domains/frontends/ai-automation-ui/Dockerfile"
  tags       = ["homeiq/ai-automation-ui:latest"]
  labels     = { "org.opencontainers.image.source" = "https://github.com/homeiq/homeiq" }
}

group "frontends" {
  targets = [
    "observability-dashboard",
    "ai-automation-ui",
  ]
}

# ──────────────────────────────────────────────
# Full build — all domains
# ──────────────────────────────────────────────

group "full" {
  targets = [
    "core-platform",
    "data-collectors",
    "ml-engine",
    "automation-core",
    "blueprints",
    "energy-analytics",
    "device-management",
    "pattern-analysis",
    "frontends",
  ]
}
