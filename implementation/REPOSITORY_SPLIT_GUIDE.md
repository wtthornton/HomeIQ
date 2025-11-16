# HomeIQ Repository Restructure Guide

## Executive Summary

This guide provides a detailed plan to create two NEW repositories for HomeIQ's go-forward architecture while **keeping the existing HomeIQ repository unchanged**:

1. **HomeIQ-Box** (Public) - On-premise components that run in customers' homes
2. **HomeIQ-Cloud** (Private) - Proprietary cloud services and AI engine

### Progress Checkpoint — November 13, 2025

- ✅ HomeIQ-Box repository initialized, populated with core edge services, shared libs, scripts, and updated Docker Compose for Epic 31 flow
- ✅ Compose variants and Box documentation refreshed to reflect the streamlined inline-normalization stack and optional AI automation block
- ✅ Local AI Automation service/UI imported as opt-in free-tier components; advanced cloud integrations remain pending
- ✅ HomeIQ-Cloud repository scaffolded (services, infra, business docs) ready for proprietary workloads
- ✅ HomeIQ-Infra README refreshed; infra codebase linked to both Box and Cloud efforts
- ⏳ Next up: scaffold initial HomeIQ-Cloud services with stubbed endpoints, define Box↔Cloud telemetry contract, and extend HomeIQ-Infra with AWS prerequisites (RDS, S3, queues) plus deployment pipelines

**Important:** The current `HomeIQ` repository will remain as-is for:
- Historical reference
- Existing development work
- Continuity of current operations
- Legacy documentation

**Strategic Rationale:**
- Build community trust through open-source edge components
- Protect competitive advantage via proprietary AI models and cloud infrastructure
- Enable community contributions while safeguarding business logic
- Create clear separation between free (local) and paid (cloud) features
- **Zero disruption** to current HomeIQ development

---

## Table of Contents

1. [Repository Structure Overview](#repository-structure-overview)
2. [Public Repository: HomeIQ-Box](#public-repository-homeiq-box)
3. [Private Repository: HomeIQ-Cloud](#private-repository-homeiq-cloud)
4. [File-by-File Migration Map](#file-by-file-migration-map)
5. [Implementation Steps](#implementation-steps)
6. [Communication Strategy](#communication-strategy)
7. [New Files to Create](#new-files-to-create)
8. [Testing & Validation](#testing--validation)
9. [Timeline & Milestones](#timeline--milestones)

---

## Repository Structure Overview

### Current State (Remains Unchanged)
```
homeiq/  (EXISTING - STAYS AS-IS)
├── services/              # All microservices
├── shared/                # Shared utilities
├── infrastructure/        # Docker configs
├── scripts/               # Setup scripts
├── tests/                 # All tests
├── docs/                  # Documentation
└── tools/                 # CLI tools

This repository continues normal development and operations.
```

### New Repositories (To Be Created)

```
┌─────────────────────────────────────┐
│  HomeIQ-Box (NEW - PUBLIC)          │
│  github.com/wtthornton/HomeIQ-Box   │
│                                     │
│  Fresh repo built from HomeIQ      │
│  Contains only edge components      │
│  + New cloud sync features          │
│  + HA Add-on packaging             │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  HomeIQ-Cloud (NEW - PRIVATE)       │
│  github.com/wtthornton/HomeIQ-Cloud │
│                                     │
│  Brand new repo                     │
│  Contains cloud services            │
│  + AI/ML infrastructure             │
│  + SaaS platform                   │
└─────────────────────────────────────┘
```

```
┌─────────────────────────────────────┐
│  HomeIQ (EXISTING - NO CHANGES)     │
│  github.com/wtthornton/HomeIQ       │
│                                     │
│  Current development continues here │
│  All existing work stays intact     │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  HomeIQ-Box (NEW - PUBLIC)          │
│  github.com/wtthornton/HomeIQ-Box   │
│                                     │
│  ├── services/                      │
│  │   ├── websocket-ingestion/      │
│  │   ├── enrichment-pipeline/      │
│  │   ├── admin-api/                │
│  │   ├── data-retention/           │
│  │   ├── health-dashboard/         │
│  │   ├── sports-data/              │
│  │   ├── log-aggregator/           │
│  │   ├── weather-api/              │
│  │   ├── carbon-intensity/         │
│  │   ├── electricity-pricing/      │
│  │   ├── air-quality/              │
│  │   ├── calendar-service/         │
│  │   ├── smart-meter/              │
│  │   ├── ha-setup-service/         │
│  │   └── ai-automation/            │
│  │       ├── pattern-detection/    │
│  │       └── local-processing/     │
│  ├── addon/              # NEW      │
│  ├── cloud-sync/         # NEW      │
│  ├── shared/                        │
│  ├── infrastructure/                │
│  ├── scripts/                       │
│  ├── tests/                         │
│  └── docs/                          │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  HomeIQ-Cloud (NEW - PRIVATE)       │
│  github.com/wtthornton/HomeIQ-Cloud │
│                                     │
│  ├── services/                      │
│  │   ├── ai-engine/                │
│  │   │   ├── suggestion-engine/    │
│  │   │   ├── predictive-models/    │
│  │   │   ├── energy-optimizer/     │
│  │   │   ├── anomaly-detector/     │
│  │   │   └── cross-home-insights/  │
│  │   ├── data-lake/                │
│  │   │   ├── ingestion/            │
│  │   │   ├── anonymization/        │
│  │   │   ├── aggregation/          │
│  │   │   └── ml-training/          │
│  │   ├── saas-api/                 │
│  │   │   ├── authentication/       │
│  │   │   ├── multi-tenant/         │
│  │   │   ├── billing/              │
│  │   │   ├── remote-access/        │
│  │   │   └── fleet-management/     │
│  │   ├── cloud-dashboard/          │
│  │   │   ├── web-app/              │
│  │   │   └── mobile-app/           │
│  │   └── admin-tools/              │
│  ├── ml-models/                    │
│  ├── infrastructure/               │
│  │   ├── kubernetes/               │
│  │   ├── terraform/                │
│  │   └── monitoring/               │
│  ├── business/                     │
│  └── docs/                         │
└─────────────────────────────────────┘
```

```
┌─────────────────────────────────────┐
│  HomeIQ-Infra (EXISTING - PUBLIC)   │
│  github.com/wtthornton/HomeIQ-Infra │
│                                     │
│  AWS/CDK infrastructure code lives  │
│  here. Make all infrastructure      │
│  changes in this repository.        │
└─────────────────────────────────────┘
```

---

## Public Repository: HomeIQ-Box

### Purpose
New open-source repository containing on-premise components that run in customers' homes. This is a **fresh copy** of the relevant parts of HomeIQ, packaged for production use.

**Relationship to HomeIQ:**
- **Source:** Copied from the existing HomeIQ repository
- **Purpose:** Production-ready edge deployment (hardware + cloud hybrid model)
- **Development:** HomeIQ continues as development repo, HomeIQ-Box is the public product

### License
**MIT License** - Maximum permissiveness to encourage adoption and contribution

### Key Principles
1. **Privacy-First**: All processing happens locally, no personal data leaves home without explicit consent
2. **Cloud-Optional**: Full functionality without cloud subscription
3. **Auditable**: Users can inspect exactly what runs in their home
4. **Community-Driven**: Accept contributions, issues, and feature requests

### Components to Keep Public

#### ✅ Core Services (All Current Services)
```
services/
├── websocket-ingestion/        # HA WebSocket client
├── enrichment-pipeline/        # Data processing & validation
├── admin-api/                  # Local REST API gateway
├── data-retention/             # Local data lifecycle management
├── health-dashboard/           # React UI (12 tabs)
├── sports-data/                # ESPN API integration
├── log-aggregator/             # Docker log collection
├── weather-api/                # OpenWeatherMap integration
├── carbon-intensity-service/   # Carbon data fetching
├── electricity-pricing-service/ # Energy pricing
├── air-quality-service/        # Air quality monitoring
├── calendar-service/           # HA calendar integration
├── smart-meter-service/        # Smart meter data
└── ha-setup-service/           # Health monitoring & setup wizards
```

**These are copied as-is from HomeIQ to HomeIQ-Box**

#### ✅ AI Automation (Split - Basic Parts Only)
```
services/ai-automation/
├── pattern-detection/          # PUBLIC - Basic pattern algorithms
│   ├── usage_patterns.py      # Simple statistical analysis
│   ├── device_analysis.py     # Device behavior tracking
│   └── local_suggestions.py   # Basic rule-based suggestions
├── local-processing/           # PUBLIC - Local data processing
│   ├── event_processor.py
│   └── cache_manager.py
└── README.md                   # Documents what's local vs cloud
```

**Note:** Advanced AI suggestion engine moves to private repo

#### ✅ New Components to Add

**1. Home Assistant Add-on Configuration**
```
addon/
├── config.yaml                 # HA Add-on definition
├── Dockerfile                  # Multi-stage build
├── run.sh                      # Startup script
├── README.md                   # Installation guide
├── CHANGELOG.md                # Version history
├── icon.png                    # Add-on icon
└── logo.png                    # Add-on logo
```

**2. Cloud Sync Agent (Transparent & Auditable)**
```
cloud-sync/
├── sync_agent.py               # Main sync logic
├── telemetry_collector.py      # What data we collect
├── privacy_controls.py         # User privacy settings
├── encryption.py               # Data encryption layer
├── anonymous_id.py             # Home ID generation
├── config.yaml                 # Sync configuration
├── README.md                   # Explains data collection
└── tests/
    ├── test_anonymization.py
    └── test_encryption.py
```

#### ✅ Shared Utilities
```
shared/
├── logging_config.py           # Structured logging
├── correlation_middleware.py   # Request tracking
├── metrics_collector.py        # Metrics framework
├── alert_manager.py            # Alert management
├── database_utils.py           # DB helper functions
└── config_loader.py            # Configuration management
```

#### ✅ Infrastructure & Deployment
```
infrastructure/
├── docker-compose.yml          # Local development
├── docker-compose.dev.yml      # Dev environment
├── docker-compose.prod.yml     # Production environment
├── .env.example                # Example configuration
└── nginx/                      # Nginx configs
```

#### ✅ Scripts & Tooling
```
scripts/
├── setup-secure-env.sh         # Environment setup
├── setup-config.sh             # Service configuration
├── start-dev.sh                # Start development
├── start-prod.sh               # Start production
├── test-services.sh            # Service testing
├── view-logs.sh                # Log viewing
├── cleanup.sh                  # Docker cleanup
└── deploy-wizard.sh            # Deployment wizard
```

#### ✅ Documentation
```
docs/
├── ARCHITECTURE.md             # System architecture
├── DEPLOYMENT_GUIDE.md         # How to deploy
├── PRIVACY.md                  # NEW - Privacy policy
├── SECURITY.md                 # NEW - Security practices
├── CONTRIBUTING.md             # NEW - Contribution guide
├── CODE_OF_CONDUCT.md          # NEW - Community guidelines
├── API_DOCUMENTATION.md        # API reference
├── TROUBLESHOOTING.md          # Common issues
├── QUICK_START.md              # Getting started
├── DOCKER_STRUCTURE_GUIDE.md   # Docker details
├── WEBSOCKET_TROUBLESHOOTING.md
└── examples/                   # Usage examples
```

#### ✅ Tests
```
tests/
├── integration/                # Integration tests
├── unit/                       # Unit tests
├── e2e/                        # End-to-end tests
└── fixtures/                   # Test data
```

---

## Private Repository: HomeIQ-Cloud

### Purpose
Proprietary cloud services, AI models, and SaaS infrastructure that provide premium features and insights learned from aggregated data across thousands of homes.

### License
**Proprietary License** - All rights reserved

### Key Principles
1. **Competitive Moat**: AI models trained on aggregate data from fleet
2. **Network Effects**: Value increases with each home connected
3. **Business Logic**: Pricing, billing, and monetization strategies
4. **Scalability**: Multi-tenant architecture for thousands of homes

### Components in Private Repository

#### ❌ AI Engine (Your Competitive Advantage)
```
services/ai-engine/
├── suggestion-engine/
│   ├── nlp_processor.py           # Natural language understanding
│   ├── automation_generator.py    # YAML automation generation
│   ├── safety_validator.py        # 6-rule safety checks
│   ├── context_manager.py         # Conversation context
│   └── models/
│       ├── suggestion_model_v3.pkl
│       └── safety_model_v2.pkl
├── predictive-maintenance/
│   ├── failure_predictor.py       # Device failure prediction
│   ├── anomaly_detector.py        # Unusual behavior detection
│   ├── health_scorer.py           # Device health scoring
│   └── models/
│       ├── hvac_failure_model.pkl
│       ├── water_heater_model.pkl
│       └── smart_switch_model.pkl
├── energy-optimizer/
│   ├── schedule_optimizer.py      # Optimal HVAC/device schedules
│   ├── pricing_analyzer.py        # Time-of-use optimization
│   ├── weather_correlator.py      # Weather-based predictions
│   └── models/
│       ├── energy_model_v4.pkl
│       └── thermal_model_v2.pkl
├── cross-home-insights/
│   ├── fleet_analyzer.py          # Aggregate pattern analysis
│   ├── benchmark_engine.py        # Compare home to fleet average
│   ├── trend_detector.py          # Emerging patterns
│   └── recommendation_engine.py   # Personalized recommendations
└── device-intelligence/
    ├── capability_detector.py     # Discover device features
    ├── feature_suggester.py       # Unused feature suggestions
    └── compatibility_checker.py   # Device compatibility
```

#### ❌ Data Lake (Multi-Home Data Processing)
```
services/data-lake/
├── ingestion/
│   ├── telemetry_receiver.py      # Receive from edge devices
│   ├── validator.py               # Data validation
│   ├── deduplicator.py            # Remove duplicates
│   └── router.py                  # Route to processing pipelines
├── anonymization/
│   ├── pii_remover.py             # Strip personal identifiers
│   ├── aggregator.py              # Aggregate raw data
│   ├── hasher.py                  # One-way hashing
│   └── privacy_auditor.py         # Ensure no PII leaks
├── storage/
│   ├── timeseries_db.py           # Time-series storage (InfluxDB/TimescaleDB)
│   ├── document_db.py             # Document storage (MongoDB)
│   ├── object_storage.py          # S3/GCS for raw data
│   └── data_warehouse.py          # Analytics warehouse (Snowflake/BigQuery)
├── ml-training/
│   ├── dataset_builder.py         # Create training datasets
│   ├── feature_engineering.py     # Feature extraction
│   ├── model_trainer.py           # Train ML models
│   ├── model_evaluator.py         # Validate models
│   └── experiment_tracker.py      # MLflow/Weights & Biases
└── analytics/
    ├── query_engine.py            # Ad-hoc queries
    ├── report_generator.py        # Automated reports
    └── dashboard_backend.py       # Analytics API
```

#### ❌ SaaS API (Multi-Tenant Backend)
```
services/saas-api/
├── authentication/
│   ├── auth_service.py            # JWT/OAuth authentication
│   ├── user_management.py         # User CRUD operations
│   ├── session_manager.py         # Session handling
│   └── mfa_handler.py             # Multi-factor authentication
├── multi-tenant/
│   ├── tenant_resolver.py         # Identify tenant from request
│   ├── isolation_middleware.py    # Data isolation enforcement
│   ├── quota_manager.py           # Usage quotas per tenant
│   └── tenant_provisioning.py     # New tenant setup
├── billing/
│   ├── stripe_integration.py      # Stripe payment processing
│   ├── subscription_manager.py    # Subscription lifecycle
│   ├── invoice_generator.py       # Invoice creation
│   ├── usage_tracker.py           # Track usage for billing
│   └── webhook_handler.py         # Stripe webhook processing
├── remote-access/
│   ├── tunnel_manager.py          # Secure tunneling to edge devices
│   ├── proxy_service.py           # Reverse proxy
│   ├── connection_pool.py         # Manage connections
│   └── security_layer.py          # Authentication & authorization
├── fleet-management/
│   ├── device_registry.py         # Track all deployed boxes
│   ├── health_monitor.py          # Monitor edge device health
│   ├── update_manager.py          # OTA updates
│   ├── diagnostics.py             # Remote diagnostics
│   └── command_dispatcher.py      # Send commands to edge devices
└── api-gateway/
    ├── rate_limiter.py            # API rate limiting
    ├── request_validator.py       # Request validation
    └── response_cache.py          # Response caching
```

#### ❌ Cloud Dashboard & Mobile Apps
```
services/cloud-dashboard/
├── web-app/                       # React/Next.js web application
│   ├── src/
│   │   ├── components/
│   │   │   ├── MultiPropertyDashboard/
│   │   │   ├── AIInsights/
│   │   │   ├── RemoteAccess/
│   │   │   └── BillingPortal/
│   │   ├── pages/
│   │   ├── services/
│   │   └── hooks/
│   ├── package.json
│   └── README.md
└── mobile-app/                    # React Native mobile app
    ├── ios/                       # iOS-specific code
    ├── android/                   # Android-specific code
    ├── src/
    │   ├── screens/
    │   ├── components/
    │   ├── services/
    │   └── navigation/
    └── package.json
```

#### ❌ Admin & Operations Tools
```
services/admin-tools/
├── customer-management/
│   ├── crm_integration.py         # Salesforce/HubSpot integration
│   ├── support_portal.py          # Customer support interface
│   └── onboarding_automation.py   # New customer onboarding
├── fleet-operations/
│   ├── monitoring_dashboard.py    # Operations dashboard
│   ├── alert_aggregator.py        # Aggregate alerts from fleet
│   ├── incident_manager.py        # Incident tracking
│   └── sla_monitor.py             # SLA compliance tracking
├── feature-flags/
│   ├── flag_manager.py            # Feature flag control
│   ├── rollout_controller.py      # Gradual rollouts
│   └── experiment_manager.py      # A/B test management
└── business-intelligence/
    ├── metrics_aggregator.py      # Business metrics
    ├── churn_analyzer.py          # Customer churn analysis
    ├── revenue_reporter.py        # Revenue analytics
    └── growth_tracker.py          # Growth metrics
```

#### ❌ ML Models & Training
```
ml-models/
├── trained-models/
│   ├── suggestion_engine_v3.2.pkl
│   ├── energy_optimizer_v2.1.pkl
│   ├── hvac_failure_v1.8.pkl
│   ├── anomaly_detector_v2.0.pkl
│   └── model_registry.json        # Model metadata
├── training-scripts/
│   ├── train_suggestion_model.py
│   ├── train_energy_model.py
│   ├── train_failure_model.py
│   └── hyperparameter_tuning.py
├── datasets/
│   ├── README.md                  # Dataset documentation
│   ├── energy_usage_dataset/
│   ├── device_failures_dataset/
│   └── automation_patterns_dataset/
└── experiments/
    └── mlflow/                    # MLflow experiment tracking
```

#### ❌ Infrastructure as Code
```
infrastructure/
├── kubernetes/
│   ├── namespaces/
│   ├── deployments/
│   ├── services/
│   ├── ingress/
│   ├── configmaps/
│   └── secrets/
├── terraform/
│   ├── aws/                       # AWS infrastructure
│   │   ├── vpc.tf
│   │   ├── eks.tf
│   │   ├── rds.tf
│   │   ├── s3.tf
│   │   └── cloudfront.tf
│   ├── gcp/                       # GCP infrastructure (if multi-cloud)
│   └── modules/                   # Reusable terraform modules
├── monitoring/
│   ├── prometheus/
│   ├── grafana/
│   ├── elasticsearch/
│   └── alertmanager/
└── ci-cd/
    ├── github-actions/
    ├── argocd/
    └── spinnaker/
```

#### ❌ Business Logic & Strategy
```
business/
├── pricing/
│   ├── pricing_models.py          # Pricing algorithms
│   ├── discount_engine.py         # Promotional discounts
│   └── tier_definitions.yaml      # Subscription tiers
├── experiments/
│   ├── ab_test_configs/           # A/B test configurations
│   ├── feature_experiments/       # Feature experiments
│   └── pricing_experiments/       # Pricing experiments
├── roadmap/
│   ├── Q1_2025.md                 # Quarterly roadmaps
│   ├── Q2_2025.md
│   └── strategic_priorities.md
└── competitive-analysis/
    ├── competitor_matrix.xlsx
    └── market_research.md
```

#### ❌ Private Documentation
```
docs/
├── ARCHITECTURE.md                # Cloud architecture
├── API_INTERNAL.md                # Internal API docs
├── ML_MODELS.md                   # Model documentation
├── DEPLOYMENT.md                  # Cloud deployment guide
├── SECURITY.md                    # Security practices
├── SCALING.md                     # Scaling strategies
├── INCIDENT_RESPONSE.md           # Incident runbooks
├── ONBOARDING.md                  # Team onboarding
└── runbooks/                      # Operational runbooks
```

---

## File-by-File Migration Map

**Important:** We are **COPYING** files from HomeIQ to create new repositories, not moving them. The original HomeIQ repo remains unchanged.

### Services Copied to HomeIQ-Box (Public)

| Source (HomeIQ) | Destination (HomeIQ-Box) | Notes |
|-----------------|--------------------------|-------|
| `services/websocket-ingestion/` | `homeiq-box/services/websocket-ingestion/` | Copy as-is |
| `services/enrichment-pipeline/` | `homeiq-box/services/enrichment-pipeline/` | Copy as-is |
| `services/admin-api/` | `homeiq-box/services/admin-api/` | Copy as-is |
| `services/data-retention/` | `homeiq-box/services/data-retention/` | Copy as-is |
| `services/health-dashboard/` | `homeiq-box/services/health-dashboard/` | Copy as-is |
| `services/sports-data/` | `homeiq-box/services/sports-data/` | Copy as-is |
| `services/log-aggregator/` | `homeiq-box/services/log-aggregator/` | Copy as-is |
| `services/weather-api/` | `homeiq-box/services/weather-api/` | Copy as-is |
| `services/carbon-intensity-service/` | `homeiq-box/services/carbon-intensity-service/` | Copy as-is |
| `services/electricity-pricing-service/` | `homeiq-box/services/electricity-pricing-service/` | Copy as-is |
| `services/air-quality-service/` | `homeiq-box/services/air-quality-service/` | Copy as-is |
| `services/calendar-service/` | `homeiq-box/services/calendar-service/` | Copy as-is |
| `services/smart-meter-service/` | `homeiq-box/services/smart-meter-service/` | Copy as-is |
| `services/ha-setup-service/` | `homeiq-box/services/ha-setup-service/` | Copy as-is |
| `shared/` | `homeiq-box/shared/` | Copy as-is |
| `infrastructure/` | `homeiq-box/infrastructure/` | Copy as-is |
| `scripts/` | `homeiq-box/scripts/` | Copy as-is |
| `tests/` | `homeiq-box/tests/` | Copy as-is |
| `docs/` | `homeiq-box/docs/` | Copy and update |
| AWS/CDK Infrastructure (`HomeIQ` root) | `HomeIQ-Infra` | Infrastructure as code owned by dedicated repo |

**Original HomeIQ:** All files remain in place, no changes

### AI Automation Components (Split Between Repos)

| Source (HomeIQ) | Public Destination | Private Destination | Strategy |
|-----------------|-------------------|---------------------|----------|
| `services/ai-automation/` | `homeiq-box/services/ai-automation/` (basic only) | `homeiq-cloud/services/ai-engine/` (advanced) | Copy basic pattern detection to public, create new advanced AI in private |

**Detailed Split for AI Automation:**

**Public (HomeIQ-Box) - Basic Features:**
```
homeiq-box/services/ai-automation/
├── pattern-detection/
│   ├── usage_patterns.py          # Statistical analysis
│   ├── device_analysis.py         # Device behavior
│   └── basic_rules.py             # Rule-based suggestions
├── local-processing/
│   ├── event_processor.py
│   └── cache_manager.py
└── README.md                       # Documents local vs cloud features
```

**Private (HomeIQ-Cloud) - Advanced Features:**
```
homeiq-cloud/services/ai-engine/
├── suggestion-engine/              # NEW - Advanced AI
│   ├── nlp_processor.py
│   ├── automation_generator.py
│   ├── safety_validator.py
│   └── models/
├── predictive-maintenance/         # NEW
├── energy-optimizer/               # NEW
├── cross-home-insights/            # NEW
└── device-intelligence/            # NEW
```

### New Components to Create in HomeIQ-Box

| Component | Location | Purpose |
|-----------|----------|---------|
| HA Add-on Config | `homeiq-box/addon/` | Package as Home Assistant Add-on |
| Cloud Sync Agent | `homeiq-box/cloud-sync/` | Transparent data sync to cloud |
| Privacy Docs | `homeiq-box/docs/PRIVACY.md` | Explain data collection |
| Security Docs | `homeiq-box/docs/SECURITY.md` | Security best practices |
| Contributing Guide | `homeiq-box/docs/CONTRIBUTING.md` | How to contribute |
| Code of Conduct | `homeiq-box/docs/CODE_OF_CONDUCT.md` | Community guidelines |

### New Components to Create in HomeIQ-Cloud

| Component | Location | Purpose |
|-----------|----------|---------|
| Cloud API | `homeiq-cloud/services/saas-api/` | Multi-tenant SaaS API |
| Data Lake | `homeiq-cloud/services/data-lake/` | Aggregate data processing |
| AI Engine | `homeiq-cloud/services/ai-engine/` | Advanced AI models |
| ML Training | `homeiq-cloud/ml-models/` | Model training pipelines |
| Infrastructure | `homeiq-cloud/infrastructure/` | K8s, Terraform configs |

---

## Implementation Steps

**Core Principle:** Create two NEW repositories while leaving HomeIQ completely untouched.

### Phase 1: Preparation (Week 1)

#### Day 1-2: Plan & Document

```bash
# 1. Document current HomeIQ structure
cd HomeIQ
tree -L 2 -d > homeiq-structure.txt

# 2. Identify what goes to each new repo
# Create mapping document (you've done this above)

# 3. Create project plan
# - Who owns each repo?
# - What's the release timeline?
# - How do we test integration?
```

#### Day 3-4: Create New GitHub Repositories

**On GitHub.com:**

1. **Create HomeIQ-Box** (Public)
   - Name: `HomeIQ-Box`
   - Description: "Production-ready Home Assistant data platform - on-premise edge computing"
   - Visibility: **Public**
   - Initialize: ❌ Do NOT initialize with README (we'll push from local)

2. **Create HomeIQ-Cloud** (Private)
   - Name: `HomeIQ-Cloud`
   - Description: "HomeIQ Cloud Services - AI engine and SaaS platform"
   - Visibility: **Private**
   - Initialize: ❌ Do NOT initialize with README

#### Day 5: Validate HomeIQ Works

```bash
# Make sure current HomeIQ is healthy before we copy
cd HomeIQ
docker-compose up -d
./scripts/test-services.sh

# Take a snapshot
git log -1 > homeiq-snapshot.txt
git status > homeiq-git-status.txt

# Tag current state (optional)
git tag -a v1.0-pre-restructure -m "State before creating Box/Cloud repos"
```

---

### Phase 2: Create HomeIQ-Box (Week 2)

#### Day 1: Initialize HomeIQ-Box Repository

```bash
# 1. Create fresh directory
cd ~/projects  # or wherever you work
mkdir homeiq-box
cd homeiq-box

# 2. Initialize git
git init
git branch -M main

# 3. Add remote
git remote add origin git@github.com:wtthornton/HomeIQ-Box.git

# 4. Create initial structure
mkdir -p services shared infrastructure scripts tests docs addon cloud-sync
```

#### Day 2-3: Copy Edge Services from HomeIQ

```bash
# Copy all edge services from HomeIQ
cd ~/projects/homeiq-box

# Copy services
cp -r ~/projects/HomeIQ/services/websocket-ingestion ./services/
cp -r ~/projects/HomeIQ/services/enrichment-pipeline ./services/
cp -r ~/projects/HomeIQ/services/admin-api ./services/
cp -r ~/projects/HomeIQ/services/data-retention ./services/
cp -r ~/projects/HomeIQ/services/health-dashboard ./services/
cp -r ~/projects/HomeIQ/services/sports-data ./services/
cp -r ~/projects/HomeIQ/services/log-aggregator ./services/
cp -r ~/projects/HomeIQ/services/weather-api ./services/
cp -r ~/projects/HomeIQ/services/carbon-intensity-service ./services/
cp -r ~/projects/HomeIQ/services/electricity-pricing-service ./services/
cp -r ~/projects/HomeIQ/services/air-quality-service ./services/
cp -r ~/projects/HomeIQ/services/calendar-service ./services/
cp -r ~/projects/HomeIQ/services/smart-meter-service ./services/
cp -r ~/projects/HomeIQ/services/ha-setup-service ./services/

# Copy basic AI automation (not advanced features)
mkdir -p ./services/ai-automation/pattern-detection
mkdir -p ./services/ai-automation/local-processing
# Copy only the basic pattern detection files
# Skip advanced suggestion engine, device intelligence, etc.

# Copy supporting infrastructure
cp -r ~/projects/HomeIQ/shared ./
cp -r ~/projects/HomeIQ/infrastructure ./
cp -r ~/projects/HomeIQ/scripts ./
cp -r ~/projects/HomeIQ/tests ./

# Copy docs (we'll update these)
cp -r ~/projects/HomeIQ/docs ./

# Copy root files
cp ~/projects/HomeIQ/docker-compose.yml ./
cp ~/projects/HomeIQ/.gitignore ./
cp ~/projects/HomeIQ/requirements.txt ./
cp ~/projects/HomeIQ/LICENSE ./
```

#### Day 4: Create New Components for HomeIQ-Box

```bash
# 1. Create HA Add-on structure
mkdir -p addon
# Create addon/config.yaml (see code in guide above)
# Create addon/Dockerfile (see code in guide above)
# Create addon/run.sh (see code in guide above)

# 2. Create Cloud Sync Agent
mkdir -p cloud-sync
# Create cloud-sync/sync_agent.py (see code in guide above)
# Create cloud-sync/telemetry_collector.py
# Create cloud-sync/privacy_controls.py
# Create cloud-sync/encryption.py
# Create cloud-sync/README.md

# 3. Add new documentation
# Create docs/PRIVACY.md (see guide above)
# Create docs/SECURITY.md
# Create docs/CONTRIBUTING.md
# Create docs/CODE_OF_CONDUCT.md
```

#### Day 5: Create HomeIQ-Box README

```bash
# Create a brand new README.md for HomeIQ-Box
cat > README.md << 'EOF'
# HomeIQ Box

**Production-ready Home Assistant data platform for on-premise deployment**

HomeIQ Box is the open-source edge component that runs in your home, providing:
- Real-time Home Assistant event processing
- Multi-source data enrichment
- Advanced analytics and dashboards
- Optional cloud AI insights

## 🚀 Quick Start

### Option 1: Home Assistant Add-on (Recommended)
1. Add this repository to Home Assistant
2. Install "HomeIQ Box" add-on
3. Configure and start

### Option 2: Docker Compose
```bash
git clone https://github.com/wtthornton/HomeIQ-Box.git
cd homeiq-box
./scripts/setup-secure-env.sh
docker-compose up -d
```

## 📖 Documentation

- [Installation Guide](docs/DEPLOYMENT_GUIDE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Privacy Policy](docs/PRIVACY.md)
- [Contributing](docs/CONTRIBUTING.md)

## 🔒 Privacy First

Everything runs locally. Cloud sync is optional and transparent.
See [PRIVACY.md](docs/PRIVACY.md) for details.

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](docs/CONTRIBUTING.md).

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🔗 Links

- **Cloud Service:** [HomeIQ Cloud](https://github.com/wtthornton/HomeIQ-Cloud) (optional)
- **Development Repo:** [HomeIQ](https://github.com/wtthornton/HomeIQ) (active development)
- **Website:** https://homeiq.io
- **Docs:** https://docs.homeiq.io

---

**Note:** This repo is the production-ready edge component. For active development and latest features, see the main [HomeIQ](https://github.com/wtthornton/HomeIQ) repository.
EOF

# Commit everything
git add .
git commit -m "Initial commit - HomeIQ Box v1.0"
git push -u origin main
```

---

### Phase 3: Create HomeIQ-Cloud (Week 3)

#### Day 1: Initialize HomeIQ-Cloud Repository

```bash
# 1. Create fresh directory
cd ~/projects
mkdir homeiq-cloud
cd homeiq-cloud

# 2. Initialize git
git init
git branch -M main

# 3. Add remote
git remote add origin git@github.com:wtthornton/HomeIQ-Cloud.git

# 4. Create structure for cloud services
mkdir -p services/ai-engine
mkdir -p services/data-lake
mkdir -p services/saas-api
mkdir -p services/cloud-dashboard
mkdir -p services/admin-tools
mkdir -p ml-models
mkdir -p infrastructure/{kubernetes,terraform,monitoring}
mkdir -p business/{pricing,experiments,roadmap}
mkdir -p docs
```

#### Day 2-3: Create Cloud Services (New Code)

```bash
# This is NEW code you'll write for cloud
# Start with basic structure

# 1. AI Engine service
cat > services/ai-engine/README.md << 'EOF'
# AI Engine

Proprietary AI models for HomeIQ Cloud:
- Suggestion Engine (NLP-powered automation generation)
- Predictive Maintenance (failure prediction)
- Energy Optimizer (schedule optimization)
- Cross-Home Insights (fleet learning)

## Models

- suggestion_engine_v3.2.pkl
- energy_optimizer_v2.1.pkl
- hvac_failure_v1.8.pkl

Training data from 1,000+ homes.
EOF

# 2. Data Lake service
cat > services/data-lake/README.md << 'EOF'
# Data Lake

Multi-tenant data ingestion and processing:
- Receives telemetry from edge devices
- Anonymizes and aggregates data
- Trains ML models
- Provides analytics

## Architecture

Edge Devices → Ingestion → Anonymization → Storage → ML Training
EOF

# 3. SaaS API service
cat > services/saas-api/README.md << 'EOF'
# SaaS API

Multi-tenant API for HomeIQ Cloud:
- Authentication & authorization
- Subscription management (Stripe)
- Remote access tunneling
- Fleet management
- Mobile app backend
EOF

# Continue creating service stubs...
```

#### Day 4: Create Infrastructure Configs

```bash
# Terraform for cloud infrastructure
cat > infrastructure/terraform/main.tf << 'EOF'
# AWS/GCP infrastructure for HomeIQ Cloud
# - EKS/GKE cluster
# - RDS/Cloud SQL databases
# - S3/GCS storage
# - Load balancers
# - Monitoring
EOF

# Kubernetes configs
cat > infrastructure/kubernetes/README.md << 'EOF'
# Kubernetes Configs

Production deployment configs for:
- AI Engine pods
- Data Lake workers
- SaaS API servers
- Ingress controllers
EOF
```

#### Day 5: Create Private README and Push

```bash
cat > README.md << 'EOF'
# HomeIQ Cloud

**Proprietary cloud services for HomeIQ**

## 🔒 Private Repository

This repository contains proprietary code for HomeIQ's cloud platform.
Access is restricted to HomeIQ team members.

## 🏗️ Architecture

- **AI Engine:** ML models trained on fleet data
- **Data Lake:** Multi-tenant data processing
- **SaaS API:** Subscription and billing backend
- **Cloud Dashboard:** Web and mobile apps
- **Infrastructure:** Kubernetes + Terraform

## 🚀 Deployment

See internal documentation in `docs/DEPLOYMENT.md`.

## 📄 License

All rights reserved. Copyright © 2025 HomeIQ, Inc.
EOF

# Commit and push
git add .
git commit -m "Initial commit - HomeIQ Cloud v1.0"
git push -u origin main
```

---

### Phase 4: Integration & Testing (Week 4)

#### Day 1-2: Test HomeIQ-Box Standalone

```bash
# Test that HomeIQ-Box works independently
cd ~/projects/homeiq-box

# Build and start
docker-compose build
docker-compose up -d

# Verify all services start
docker-compose ps

# Test each service
curl http://localhost:8003/health  # Admin API
curl http://localhost:3000         # Dashboard
# ... test other services

# Verify no cloud dependencies
# - Should work without internet
# - All features functional locally
```

#### Day 3: Test Cloud Sync (Optional)

```bash
# Test edge → cloud communication

# 1. Start cloud services (dev mode)
cd ~/projects/homeiq-cloud
docker-compose -f docker-compose.dev.yml up -d

# 2. Configure edge to connect to local cloud
cd ~/projects/homeiq-box
export CLOUD_SYNC_ENABLED=true
export CLOUD_API_URL=http://localhost:8080
export CLOUD_API_KEY=dev-test-key

# 3. Restart edge with cloud sync
docker-compose restart

# 4. Verify sync works
docker logs homeiq_cloud_sync --tail=100
# Look for "Telemetry sent successfully"
```

#### Day 4-5: Documentation Updates

```bash
# Update all documentation across repos

# In HomeIQ (no changes to code, just add note)
cd ~/projects/HomeIQ
cat >> README.md << 'EOF'

---

## 📦 Production Deployment

For production deployment, use the **[HomeIQ-Box](https://github.com/wtthornton/HomeIQ-Box)** repository.

This repository (HomeIQ) is for active development.
EOF

git add README.md
git commit -m "Add note about HomeIQ-Box for production"
git push

# In HomeIQ-Box - finalize docs
cd ~/projects/homeiq-box
# Update all docs to reference correct repos

# In HomeIQ-Cloud - add internal docs
cd ~/projects/homeiq-cloud
# Create comprehensive internal documentation
```

---

### Phase 5: Launch & Communication (Week 5)

#### Day 1: Soft Launch

```bash
# Make repos accessible
# - HomeIQ-Box is already public
# - HomeIQ-Cloud stays private
# - HomeIQ continues development

# Tag releases
cd ~/projects/homeiq-box
git tag -a v1.0.0 -m "Initial public release"
git push origin v1.0.0

cd ~/projects/homeiq-cloud
git tag -a v1.0.0 -m "Initial private release"
git push origin v1.0.0
```

#### Day 2-3: Community Communication

**Post to HomeIQ repository:**

```markdown
# 📢 Introducing HomeIQ-Box: Production-Ready Edge Platform

We're excited to announce **[HomeIQ-Box](https://github.com/wtthornton/HomeIQ-Box)**, 
a production-ready, open-source edge platform for Home Assistant!

## What's New?

**HomeIQ-Box** is a refined, stable version of HomeIQ designed for:
- ✅ Easy installation (Home Assistant Add-on or Docker)
- ✅ Production use (tested, documented, supported)
- ✅ Optional cloud features (AI insights, remote access)

## Repositories Explained

Going forward, we have three repos:

1. **[HomeIQ](https://github.com/wtthornton/HomeIQ)** (this repo)
   - Active development
   - Experimental features
   - Latest code (may be unstable)

2. **[HomeIQ-Box](https://github.com/wtthornton/HomeIQ-Box)** (NEW - public)
   - Production deployment
   - Stable, tested releases
   - Open source (MIT)

3. **[HomeIQ-Cloud](https://github.com/wtthornton/HomeIQ-Cloud)** (NEW - private)
   - Optional cloud services
   - AI models & SaaS platform
   - Proprietary

## Which Should I Use?

- **Want to use HomeIQ?** → [HomeIQ-Box](https://github.com/wtthornton/HomeIQ-Box)
- **Want to contribute?** → Either repo! HomeIQ for new features, Box for fixes
- **Want cloud features?** → Use HomeIQ-Box + optional Cloud subscription

## Nothing Changes for Current Users

If you're already using HomeIQ, you can:
- ✅ Keep using this repo (works as before)
- ✅ Switch to HomeIQ-Box (recommended for stability)
- ✅ Contribute to either repo

## Questions?

Drop them below! 🙌

---

*This structure lets us move faster on development (HomeIQ) while providing 
a stable product (HomeIQ-Box), with optional premium features (HomeIQ-Cloud).*
```

#### Day 4-5: Monitor & Support

- Answer questions in discussions
- Fix any bugs discovered
- Update documentation based on feedback
- Plan next features

---

#### Create Home Assistant Add-on

**File: `homeiq-edge/addon/config.yaml`**
```yaml
name: "HomeIQ"
description: "Enterprise-grade data platform for Home Assistant"
version: "1.0.0"
slug: "homeiq"
init: false
arch:
  - amd64
  - aarch64
  - armv7
url: "https://github.com/wtthornton/HomeIQ"
startup: services
boot: auto
ports:
  3000/tcp: 3000
  8001/tcp: 8001
  8002/tcp: 8002
  8003/tcp: 8003
  8005/tcp: 8005
  8020/tcp: 8020
ports_description:
  3000/tcp: "Health Dashboard"
  8001/tcp: "WebSocket Ingestion"
  8002/tcp: "Enrichment Pipeline"
  8003/tcp: "Admin API"
  8005/tcp: "Sports Data API"
  8020/tcp: "HA Setup Service"
map:
  - ssl
hassio_api: true
homeassistant_api: true
auth_api: true
ingress: true
ingress_port: 3000
panel_icon: mdi:home-analytics
panel_title: HomeIQ
options:
  cloud_sync_enabled: false
  telemetry_level: "standard"
  log_level: "info"
schema:
  cloud_sync_enabled: bool
  cloud_api_key: str?
  telemetry_level: list(minimal|standard|detailed)
  log_level: list(debug|info|warning|error)
image: "ghcr.io/wtthornton/homeiq-{arch}"
```

**File: `homeiq-edge/addon/Dockerfile`**
```dockerfile
ARG BUILD_FROM
FROM $BUILD_FROM

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    nodejs \
    npm \
    docker-cli \
    curl \
    bash

# Copy requirements
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY services/ /app/services/
COPY shared/ /app/shared/
COPY cloud-sync/ /app/cloud-sync/
COPY infrastructure/ /app/infrastructure/

# Copy run script
COPY addon/run.sh /
RUN chmod a+x /run.sh

# Labels
LABEL \
    io.hass.name="HomeIQ" \
    io.hass.description="Enterprise data platform for Home Assistant" \
    io.hass.version="1.0.0" \
    io.hass.type="addon" \
    io.hass.arch="amd64|aarch64|armv7"

CMD [ "/run.sh" ]
```

**File: `homeiq-edge/addon/run.sh`**
```bash
#!/usr/bin/with-contenv bashio

# Get configuration
CLOUD_SYNC_ENABLED=$(bashio::config 'cloud_sync_enabled')
CLOUD_API_KEY=$(bashio::config 'cloud_api_key')
TELEMETRY_LEVEL=$(bashio::config 'telemetry_level')
LOG_LEVEL=$(bashio::config 'log_level')

# Get Home Assistant details
HA_TOKEN="${SUPERVISOR_TOKEN}"
HA_URL="http://supervisor/core"

# Set environment variables
export HOME_ASSISTANT_TOKEN="${HA_TOKEN}"
export HOME_ASSISTANT_URL="${HA_URL}"
export CLOUD_SYNC_ENABLED="${CLOUD_SYNC_ENABLED}"
export CLOUD_API_KEY="${CLOUD_API_KEY}"
export TELEMETRY_LEVEL="${TELEMETRY_LEVEL}"
export LOG_LEVEL="${LOG_LEVEL}"

bashio::log.info "Starting HomeIQ..."
bashio::log.info "Cloud Sync: ${CLOUD_SYNC_ENABLED}"
bashio::log.info "Telemetry Level: ${TELEMETRY_LEVEL}"

# Start services using docker-compose
cd /app
exec docker-compose -f infrastructure/docker-compose.yml up
```

#### Create Cloud Sync Agent

**File: `homeiq-edge/cloud-sync/sync_agent.py`**
```python
"""
HomeIQ Cloud Sync Agent

This module handles synchronization of anonymized telemetry data
from the edge device to the HomeIQ cloud for AI processing and insights.

PRIVACY NOTICE:
- All data is anonymized before transmission
- No personal identifiable information (PII) is sent
- Users can disable cloud sync at any time
- All data transmission is encrypted (TLS 1.3)

For details on what data is collected, see: docs/PRIVACY.md
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
import aiohttp

from .privacy_controls import PrivacyControls
from .telemetry_collector import TelemetryCollector
from .encryption import EncryptionManager

logger = logging.getLogger(__name__)


class CloudSyncAgent:
    """
    Manages synchronization of anonymized data to HomeIQ Cloud.
    
    This agent:
    1. Collects aggregated metrics (no raw events)
    2. Anonymizes all data before transmission
    3. Encrypts data in transit
    4. Respects user privacy settings
    5. Handles connection failures gracefully
    """
    
    def __init__(
        self,
        cloud_url: str = "https://api.homeiq.io",
        api_key: Optional[str] = None,
        sync_interval: int = 3600  # 1 hour
    ):
        self.cloud_url = cloud_url
        self.api_key = api_key
        self.sync_interval = sync_interval
        
        # Generate anonymous home ID (persistent)
        self.home_id = self._get_or_create_home_id()
        
        # Initialize components
        self.privacy_controls = PrivacyControls()
        self.telemetry_collector = TelemetryCollector()
        self.encryption_manager = EncryptionManager()
        
        logger.info(f"Cloud Sync Agent initialized (Home ID: {self.home_id[:8]}...)")
    
    def _get_or_create_home_id(self) -> str:
        """
        Generate or retrieve anonymous home identifier.
        
        This ID is used to track data from the same home over time
        without revealing any personal information.
        """
        home_id_file = "/config/.homeiq_home_id"
        
        try:
            with open(home_id_file, 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            # Generate new anonymous ID
            import uuid
            home_id = str(uuid.uuid4())
            
            with open(home_id_file, 'w') as f:
                f.write(home_id)
            
            logger.info(f"Generated new anonymous home ID: {home_id[:8]}...")
            return home_id
    
    async def start(self):
        """Start the sync agent background task."""
        logger.info("Starting cloud sync agent...")
        
        while True:
            try:
                # Check if cloud sync is enabled
                if not self.privacy_controls.is_cloud_sync_enabled():
                    logger.debug("Cloud sync disabled, skipping...")
                    await asyncio.sleep(self.sync_interval)
                    continue
                
                # Collect and send telemetry
                await self._sync_telemetry()
                
            except Exception as e:
                logger.error(f"Error in sync loop: {e}", exc_info=True)
            
            # Wait for next sync interval
            await asyncio.sleep(self.sync_interval)
    
    async def _sync_telemetry(self):
        """
        Collect anonymized telemetry and send to cloud.
        
        What we collect:
        - Aggregated metrics (counts, averages, sums)
        - Device types (not names or locations)
        - Performance metrics
        - Error rates
        
        What we DON'T collect:
        - Raw sensor events
        - Personal identifiers
        - Device names or locations
        - Presence/occupancy data
        - Camera feeds or images
        """
        logger.info("Collecting telemetry...")
        
        # Collect data based on privacy settings
        telemetry = await self.telemetry_collector.collect(
            privacy_level=self.privacy_controls.get_telemetry_level()
        )
        
        if not telemetry:
            logger.warning("No telemetry data collected")
            return
        
        # Add metadata
        payload = {
            "home_id": self.home_id,
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "telemetry": telemetry
        }
        
        # Log what we're sending (for transparency)
        logger.info(f"Sending telemetry: {json.dumps(payload, indent=2)}")
        
        # Encrypt payload
        encrypted_payload = self.encryption_manager.encrypt(payload)
        
        # Send to cloud
        await self._send_to_cloud(encrypted_payload)
    
    async def _send_to_cloud(self, encrypted_payload: bytes):
        """Send encrypted telemetry to cloud API."""
        headers = {
            "Content-Type": "application/octet-stream",
            "X-HomeIQ-Version": "1.0.0",
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.cloud_url}/v1/telemetry",
                    data=encrypted_payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        logger.info("Telemetry sent successfully")
                        result = await response.json()
                        
                        # Check for AI insights in response
                        if "insights" in result:
                            logger.info(f"Received {len(result['insights'])} AI insights")
                            # TODO: Store insights for user
                    else:
                        logger.error(f"Failed to send telemetry: {response.status}")
                        error_text = await response.text()
                        logger.error(f"Error response: {error_text}")
        
        except asyncio.TimeoutError:
            logger.error("Timeout sending telemetry to cloud")
        except Exception as e:
            logger.error(f"Error sending telemetry: {e}", exc_info=True)


# Example usage
if __name__ == "__main__":
    import os
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create agent
    agent = CloudSyncAgent(
        cloud_url=os.getenv("HOMEIQ_CLOUD_URL", "https://api.homeiq.io"),
        api_key=os.getenv("HOMEIQ_API_KEY"),
        sync_interval=3600  # 1 hour
    )
    
    # Run sync agent
    asyncio.run(agent.start())
```

**File: `homeiq-edge/cloud-sync/telemetry_collector.py`**
```python
"""
Telemetry Collector

Collects anonymized, aggregated metrics from HomeIQ services.
NO raw events or personal data is collected.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
import aiosqlite
from influxdb_client import InfluxDBClient

logger = logging.getLogger(__name__)


class TelemetryCollector:
    """Collects anonymized telemetry data."""
    
    def __init__(self):
        self.influxdb_client = None  # Initialize from config
        self.sqlite_path = "/data/metadata.db"
    
    async def collect(self, privacy_level: str = "standard") -> Dict[str, Any]:
        """
        Collect telemetry based on privacy level.
        
        Privacy Levels:
        - minimal: Only counts and basic metrics
        - standard: Include device types and performance metrics
        - detailed: Include patterns and usage analytics (no PII)
        """
        telemetry = {
            "privacy_level": privacy_level,
            "metrics": await self._collect_metrics(),
        }
        
        if privacy_level in ["standard", "detailed"]:
            telemetry["device_summary"] = await self._collect_device_summary()
            telemetry["performance"] = await self._collect_performance()
        
        if privacy_level == "detailed":
            telemetry["patterns"] = await self._collect_patterns()
        
        return telemetry
    
    async def _collect_metrics(self) -> Dict[str, Any]:
        """Collect basic aggregate metrics."""
        # Get last hour of data
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)
        
        return {
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "events_processed": await self._count_events(start_time, end_time),
            "automations_triggered": await self._count_automations(start_time, end_time),
            "api_requests": await self._count_api_requests(start_time, end_time),
            "errors": await self._count_errors(start_time, end_time),
        }
    
    async def _collect_device_summary(self) -> Dict[str, Any]:
        """Collect anonymized device summary (types only, no names)."""
        async with aiosqlite.connect(self.sqlite_path) as db:
            # Count devices by type
            cursor = await db.execute("""
                SELECT device_type, COUNT(*) as count
                FROM devices
                GROUP BY device_type
            """)
            device_types = await cursor.fetchall()
            
            return {
                "total_devices": sum(count for _, count in device_types),
                "device_types": {
                    device_type: count 
                    for device_type, count in device_types
                }
            }
    
    async def _collect_performance(self) -> Dict[str, Any]:
        """Collect performance metrics."""
        return {
            "avg_response_time_ms": await self._get_avg_response_time(),
            "cpu_usage_percent": await self._get_cpu_usage(),
            "memory_usage_mb": await self._get_memory_usage(),
            "disk_usage_percent": await self._get_disk_usage(),
        }
    
    async def _collect_patterns(self) -> Dict[str, Any]:
        """Collect usage patterns (anonymized)."""
        return {
            "peak_hours": await self._get_peak_hours(),
            "automation_frequency": await self._get_automation_frequency(),
            "most_used_integrations": await self._get_top_integrations(),
        }
    
    # Helper methods (implement these based on your data sources)
    async def _count_events(self, start, end) -> int:
        """Count events in time range."""
        # Query InfluxDB or your time-series DB
        return 0  # Placeholder
    
    async def _count_automations(self, start, end) -> int:
        """Count automation triggers."""
        return 0  # Placeholder
    
    async def _count_api_requests(self, start, end) -> int:
        """Count API requests."""
        return 0  # Placeholder
    
    async def _count_errors(self, start, end) -> int:
        """Count errors."""
        return 0  # Placeholder
    
    async def _get_avg_response_time(self) -> float:
        """Get average API response time."""
        return 0.0  # Placeholder
    
    async def _get_cpu_usage(self) -> float:
        """Get CPU usage percentage."""
        return 0.0  # Placeholder
    
    async def _get_memory_usage(self) -> int:
        """Get memory usage in MB."""
        return 0  # Placeholder
    
    async def _get_disk_usage(self) -> float:
        """Get disk usage percentage."""
        return 0.0  # Placeholder
    
    async def _get_peak_hours(self) -> List[int]:
        """Get peak usage hours."""
        return []  # Placeholder
    
    async def _get_automation_frequency(self) -> Dict[str, int]:
        """Get automation trigger frequencies."""
        return {}  # Placeholder
    
    async def _get_top_integrations(self) -> List[str]:
        """Get most used integrations."""
        return []  # Placeholder
```

**File: `homeiq-edge/cloud-sync/privacy_controls.py`**
```python
"""
Privacy Controls

Manages user privacy settings for cloud sync.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


class PrivacyControls:
    """Manages user privacy settings."""
    
    def __init__(self, config_path: str = "/config/privacy_settings.json"):
        self.config_path = Path(config_path)
        self.settings = self._load_settings()
    
    def _load_settings(self) -> Dict[str, Any]:
        """Load privacy settings from file."""
        if not self.config_path.exists():
            # Create default settings
            default_settings = {
                "cloud_sync_enabled": False,
                "telemetry_level": "standard",  # minimal, standard, detailed
                "share_device_types": True,
                "share_energy_data": True,
                "share_behavioral_patterns": False,  # Opt-in
                "data_retention_days": 90,
            }
            self._save_settings(default_settings)
            return default_settings
        
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading privacy settings: {e}")
            return {}
    
    def _save_settings(self, settings: Dict[str, Any]):
        """Save privacy settings to file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving privacy settings: {e}")
    
    def is_cloud_sync_enabled(self) -> bool:
        """Check if cloud sync is enabled."""
        return self.settings.get("cloud_sync_enabled", False)
    
    def get_telemetry_level(self) -> str:
        """Get telemetry collection level."""
        return self.settings.get("telemetry_level", "standard")
    
    def should_share_device_types(self) -> bool:
        """Check if device types should be shared."""
        return self.settings.get("share_device_types", True)
    
    def should_share_energy_data(self) -> bool:
        """Check if energy data should be shared."""
        return self.settings.get("share_energy_data", True)
    
    def should_share_behavioral_patterns(self) -> bool:
        """Check if behavioral patterns should be shared."""
        return self.settings.get("share_behavioral_patterns", False)
    
    def update_settings(self, new_settings: Dict[str, Any]):
        """Update privacy settings."""
        self.settings.update(new_settings)
        self._save_settings(self.settings)
        logger.info(f"Privacy settings updated: {new_settings}")
```

**File: `homeiq-edge/cloud-sync/encryption.py`**
```python
"""
Encryption Manager

Handles encryption of data before transmission to cloud.
"""

import os
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import json

logger = logging.getLogger(__name__)


class EncryptionManager:
    """Manages encryption of telemetry data."""
    
    def __init__(self):
        self.key = self._get_or_create_key()
        self.cipher = Fernet(self.key)
    
    def _get_or_create_key(self) -> bytes:
        """Get or create encryption key."""
        key_file = "/config/.homeiq_encryption_key"
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        
        # Generate new key
        key = Fernet.generate_key()
        
        with open(key_file, 'wb') as f:
            f.write(key)
        
        logger.info("Generated new encryption key")
        return key
    
    def encrypt(self, data: dict) -> bytes:
        """Encrypt telemetry data."""
        try:
            # Convert to JSON string
            json_data = json.dumps(data)
            
            # Encrypt
            encrypted = self.cipher.encrypt(json_data.encode())
            
            return encrypted
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise
    
    def decrypt(self, encrypted_data: bytes) -> dict:
        """Decrypt telemetry data (for testing)."""
        try:
            # Decrypt
            decrypted = self.cipher.decrypt(encrypted_data)
            
            # Parse JSON
            data = json.loads(decrypted.decode())
            
            return data
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise
```

#### Create Privacy Documentation

**File: `homeiq-edge/docs/PRIVACY.md`**
```markdown
# HomeIQ Privacy Policy

## Our Commitment to Privacy

HomeIQ is built with privacy as a fundamental principle. Your home is your sanctuary, and your data should remain yours. This document explains exactly what data we collect, how we use it, and how you maintain control.

## TL;DR

- ✅ **Everything runs locally first** - Your home data never leaves your network unless you explicitly enable cloud features
- ✅ **Anonymized aggregation only** - We collect patterns, not personal events
- ✅ **No PII ever** - We never collect names, addresses, camera feeds, or personally identifiable information
- ✅ **You control everything** - Toggle cloud sync on/off anytime, choose what to share
- ✅ **Open source sync agent** - Audit exactly what data leaves your home in [`cloud-sync/sync_agent.py`](../cloud-sync/sync_agent.py)

## Architecture Overview

```
┌────────────────────────────────────┐
│ YOUR HOME (All Data Stays Here)   │
│                                    │
│ ┌────────────────────────────────┐ │
│ │ Home Assistant                 │ │
│ │ - Your devices                 │ │
│ │ - Your automations             │ │
│ │ - Your schedules               │ │
│ └────────────────────────────────┘ │
│            ↓ (local network)       │
│ ┌────────────────────────────────┐ │
│ │ HomeIQ Edge                    │ │
│ │ - Processes data locally       │ │
│ │ - Stores in local databases    │ │
│ │ - Runs automations locally     │ │
│ │ - Works WITHOUT internet       │ │
│ └────────────────────────────────┘ │
│            ↓ (optional, encrypted) │
└────────────────────────────────────┘
             ↓
┌────────────────────────────────────┐
│ HomeIQ Cloud (Optional)            │
│ - Receives anonymized metrics      │
│ - Trains AI models on aggregate    │
│ - Returns insights and suggestions │
│ - NO personal data                 │
└────────────────────────────────────┘
```

## What Data We Collect

### Level 1: Minimal (Default when cloud is OFF)
**NO data leaves your home.** Everything runs locally.

### Level 2: Standard (Default when cloud is ON)
We collect **aggregated, anonymized metrics only**:

#### ✅ What We DO Collect:
- **Anonymous home identifier** - A random UUID with no connection to you
- **Device counts by type** - "15 lights, 3 thermostats, 2 door locks" (no names, locations)
- **Aggregate metrics** - "250 events/hour, 45 automations triggered/day"
- **Performance metrics** - "Average API response time: 23ms"
- **Energy usage totals** - "Used 18.5 kWh today" (no timing patterns)
- **Error rates** - "2 errors in last hour"

#### ❌ What We NEVER Collect:
- ❌ Device names or locations - "Kitchen Light" stays private
- ❌ Sensor values or states - We don't know if your door is locked/unlocked
- ❌ Presence or occupancy - We don't know when you're home
- ❌ Camera feeds or images - Never, ever
- ❌ Voice recordings - Never
- ❌ Personal schedules - We don't know your routines
- ❌ Passwords or access codes - Never stored or transmitted
- ❌ Names, emails, addresses - No PII
- ❌ Raw sensor events - Only aggregates
- ❌ Location data - We don't track where you are

### Level 3: Detailed (Opt-in Only)
Adds usage patterns for better AI insights:

- **Peak usage hours** - "Most active 6-8 PM" (no specific events)
- **Automation patterns** - "Lighting automation runs 10x/day on average"
- **Integration usage** - "Uses weather service 24x/day"

**Still NO personal data, identifiers, or raw events.**

## Example: What We See vs What We Don't

### ❌ What We DON'T See:
```json
{
  "timestamp": "2025-11-10T19:32:15Z",
  "device": "Front Door Lock",
  "state": "unlocked",
  "user": "John Smith",
  "location": "123 Main St, Anytown"
}
```

### ✅ What We DO See:
```json
{
  "home_id": "anonymous-uuid-12345",
  "timestamp": "2025-11-10T19:00:00Z",
  "metrics": {
    "events_processed_last_hour": 234,
    "automations_triggered": 12,
    "avg_response_time_ms": 23,
    "device_counts": {
      "light": 15,
      "lock": 2,
      "thermostat": 3
    }
  }
}
```

## How We Use Your Data

### Local Processing (Always)
- **Real-time automation** - Trigger automations instantly
- **Local dashboards** - View your data in real-time
- **Historical analysis** - Query your local databases

### Cloud Processing (Optional)
1. **AI Model Training** - We train models on aggregate patterns from thousands of homes to:
   - Predict device failures before they happen
   - Optimize energy usage schedules
   - Suggest automations you haven't thought of
   - Detect anomalies that could indicate problems

2. **Personalized Insights** - Based on fleet data, we provide:
   - "Your HVAC runs 40% more than similar homes - here's why"
   - "This water heater pattern suggests failure in 2 weeks"
   - "You could save $40/month by shifting usage to off-peak hours"

3. **Product Improvement** - Aggregate metrics help us:
   - Identify bugs and performance issues
   - Prioritize new features
   - Improve reliability

## Your Privacy Controls

You have complete control over data collection:

### 1. Disable Cloud Sync Entirely
```yaml
# In HomeIQ settings
cloud_sync_enabled: false
```
**Result:** NO data leaves your home. Everything works locally.

### 2. Choose Telemetry Level
```yaml
telemetry_level: "minimal"  # or "standard" or "detailed"
```

### 3. Granular Controls
```yaml
share_device_types: true      # Share "15 lights, 3 thermostats"
share_energy_data: true       # Share energy usage totals
share_behavioral_patterns: false  # Don't share usage patterns
```

### 4. View What's Being Sent
All telemetry is logged locally before transmission:
```bash
# View sync logs
docker logs homeiq_cloud_sync

# See exactly what's being sent
tail -f /config/logs/cloud_sync.log
```

### 5. Audit the Code
The sync agent is [open source](../cloud-sync/sync_agent.py). You can:
- Review exactly what data is collected
- Verify no PII is transmitted
- Contribute improvements
- Fork and modify if desired

## Data Security

### Encryption in Transit
- All data encrypted with **TLS 1.3**
- Perfect forward secrecy
- Certificate pinning

### Encryption at Rest
- Cloud data encrypted with **AES-256**
- Separate encryption keys per home
- Keys managed by AWS KMS

### Access Controls
- **Zero-trust architecture**
- Multi-factor authentication required
- Audit logs for all data access
- Regular security audits

## Data Retention

### Edge (Your Home)
- **You control retention** - Configure in data-retention service
- Default: 90 days for time-series, indefinite for metadata
- Can export or delete anytime

### Cloud
- **Aggregated metrics:** Retained indefinitely (anonymized)
- **Individual home data:** Deleted 90 days after subscription ends
- **Backups:** Encrypted, deleted after 1 year

## Your Rights

### 1. Access Your Data
Request a copy of all data associated with your home ID.

### 2. Delete Your Data
Request deletion of all cloud data. Takes effect within 30 days.

### 3. Export Your Data
Download all your data in JSON format.

### 4. Opt-Out
Disable cloud sync anytime - takes effect immediately.

### 5. Be Informed
This privacy policy will be updated when collection practices change.

## Compliance

HomeIQ is designed to comply with:
- **GDPR** (EU General Data Protection Regulation)
- **CCPA** (California Consumer Privacy Act)
- **PIPEDA** (Canadian Personal Information Protection)

## Third-Party Services

HomeIQ Edge may connect to external services **at your direction**:
- **OpenWeatherMap** - Weather data (you provide API key)
- **ESPN** - Sports scores (public data)
- **National Grid** - Carbon intensity (public data)

These connections are **optional** and controlled by you. HomeIQ does not share your data with these services beyond what's required for the service to function.

## Children's Privacy

HomeIQ does not knowingly collect data from children under 13. If cloud sync is enabled in a household with children, no personal data about children is collected.

## Changes to This Policy

We will notify users of material changes via:
- In-app notification
- Email (if provided)
- GitHub repository changelog

## Contact

Questions about privacy?
- **GitHub Issues:** https://github.com/wtthornton/HomeIQ/issues
- **Email:** privacy@homeiq.io
- **Documentation:** https://docs.homeiq.io/privacy

## Open Source Transparency

Unlike most smart home platforms, HomeIQ's edge software is **fully open source**. You can:
- **Audit the code** - See exactly what runs in your home
- **Verify our claims** - Check that we only collect what we say
- **Contribute improvements** - Help make HomeIQ more privacy-friendly
- **Fork and modify** - Make it work exactly how you want

**Edge Repository:** https://github.com/wtthornton/HomeIQ

---

*Last Updated: November 10, 2025*

**The Bottom Line:** Your home data is yours. HomeIQ works great without cloud connectivity. If you choose to enable cloud features, we only collect anonymized, aggregated metrics to improve AI insights for everyone. You can disable it anytime.
```

### Phase 4: Update Documentation (Week 4)

#### Update Main READMEs

**File: `homeiq-edge/README.md`** (Update existing)
```markdown
# HomeIQ Edge

**Enterprise-grade data ingestion platform for Home Assistant**

HomeIQ is an open-source data platform that captures, processes, and analyzes Home Assistant events with advanced filtering, transformation, and monitoring capabilities.

## 🎯 What is HomeIQ?

HomeIQ Edge is the on-premise component that runs in your home. It:
- Ingests Home Assistant events in real-time
- Processes and enriches data from multiple sources
- Provides powerful dashboards and analytics
- Runs completely locally (internet optional)
- Integrates with optional HomeIQ Cloud for AI insights

## 🏗️ Architecture

```
Home Assistant → HomeIQ Edge → Local Dashboards
                     ↓ (optional)
              HomeIQ Cloud (AI Insights)
```

**Two Components:**
1. **HomeIQ Edge** (this repo) - Open source, runs in your home
2. **HomeIQ Cloud** (optional) - Proprietary AI service for advanced insights

## 🚀 Quick Start

### Option 1: Home Assistant Add-on (Easiest)
```bash
# 1. Add HomeIQ repository in Home Assistant
# 2. Install HomeIQ add-on
# 3. Configure and start
```

### Option 2: Docker Compose
```bash
# 1. Clone repository
git clone https://github.com/wtthornton/HomeIQ.git
cd HomeIQ

# 2. Configure environment
./scripts/setup-secure-env.sh

# 3. Start services
docker-compose up -d

# 4. Access dashboard
open http://localhost:3000
```

## ✨ Features

### Core Features (Free, Open Source)
- ✅ Real-time Home Assistant event ingestion
- ✅ Multi-source data enrichment (weather, carbon, pricing, etc.)
- ✅ Hybrid database architecture (InfluxDB + SQLite)
- ✅ 12-tab interactive dashboard
- ✅ RESTful APIs for all services
- ✅ Advanced pattern detection
- ✅ Automated health monitoring
- ✅ Setup wizards for integrations

### Cloud Features (Optional Subscription)
- 🤖 AI-powered automation suggestions
- 📊 Cross-home insights and benchmarking
- 🔮 Predictive maintenance
- ⚡ Energy optimization
- 📱 Mobile app access
- 🌍 Remote access from anywhere

## 🔒 Privacy First

- **Everything runs locally** - Works without internet
- **No data leaves your home** by default
- **Transparent data collection** - Audit the sync agent code
- **You control everything** - Toggle cloud features on/off
- **Open source edge** - Inspect what runs in your home

Read our [Privacy Policy](docs/PRIVACY.md) for details.

## 📚 Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md)
- [Privacy Policy](docs/PRIVACY.md)
- [Security](docs/SECURITY.md)
- [Contributing](docs/CONTRIBUTING.md)
- [API Documentation](docs/API_DOCUMENTATION.md)

## 🤝 Contributing

HomeIQ Edge is open source! We welcome contributions.

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

## 📦 What's Included

### Services
- **websocket-ingestion** - HA WebSocket client
- **enrichment-pipeline** - Data processing
- **admin-api** - REST API gateway
- **health-dashboard** - React UI
- **sports-data** - ESPN integration
- **weather-api** - Weather enrichment
- **ai-automation** - Local pattern detection
- And 10+ more services

### Databases
- **InfluxDB** - Time-series data
- **SQLite** - Metadata & registry

### Integrations
- Home Assistant (WebSocket, REST, MQTT)
- OpenWeatherMap
- ESPN (sports)
- National Grid (carbon)
- Calendar (Google, iCloud, etc.)
- And more...

## 🌟 Why HomeIQ?

| Feature | Basic HA | HomeIQ Edge | HomeIQ Cloud |
|---------|----------|-------------|--------------|
| Real-time events | ✅ | ✅ | ✅ |
| Historical data | Limited | Unlimited | Unlimited |
| Multi-source enrichment | ❌ | ✅ | ✅ |
| Advanced dashboards | ❌ | ✅ | ✅ |
| Pattern detection | ❌ | Basic | Advanced AI |
| Predictive insights | ❌ | ❌ | ✅ |
| Cross-home learning | ❌ | ❌ | ✅ |
| Remote access | Complex | ❌ | ✅ |

## 💰 Pricing

**HomeIQ Edge:** Free forever (open source)  
**HomeIQ Cloud:** $19/month or $199/year (optional)

## 🔗 Links

- **Website:** https://homeiq.io
- **Documentation:** https://docs.homeiq.io
- **Community:** https://community.homeiq.io
- **Cloud Service:** https://cloud.homeiq.io

## 📄 License

HomeIQ Edge is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

Built with ❤️ by the HomeIQ community and powered by:
- Home Assistant
- InfluxDB
- Docker
- React
- And many more open source projects

---

**Get Started:** [Installation Guide](docs/DEPLOYMENT_GUIDE.md) | **Questions?** [Open an Issue](https://github.com/wtthornton/HomeIQ/issues)
```

**File: `homeiq-cloud/README.md`** (New file)
```markdown
# HomeIQ Cloud

**Proprietary AI-powered insights for HomeIQ**

This is the private repository containing HomeIQ's cloud services, AI models, and SaaS infrastructure.

## 🔒 Private Repository

This repository contains proprietary code and is not publicly accessible.

## 🏗️ Architecture

HomeIQ Cloud provides premium features on top of the open-source HomeIQ Edge:
- AI-powered automation suggestions
- Predictive maintenance
- Energy optimization
- Cross-home insights
- Remote access
- Mobile apps

## 📁 Repository Structure

```
homeiq-cloud/
├── services/
│   ├── ai-engine/          # ML models and inference
│   ├── data-lake/          # Multi-tenant data processing
│   ├── saas-api/           # SaaS backend
│   ├── cloud-dashboard/    # Web and mobile apps
│   └── admin-tools/        # Operations tools
├── ml-models/              # Trained models
├── infrastructure/         # K8s, Terraform, etc.
└── business/               # Pricing, roadmap, etc.
```

## 🚀 Deployment

See internal documentation for deployment procedures.

## 🔑 Access

Access to this repository is restricted to HomeIQ team members.

## 📄 License

All rights reserved. Copyright © 2025 HomeIQ, Inc.
```

## Communication Strategy

### Announcement to Community

**GitHub Discussion Post:**
```markdown
# 📢 HomeIQ Repository Restructuring

Hey HomeIQ community! 👋

We're excited to announce a major restructuring that will benefit both our open-source users and those using HomeIQ Cloud.

## What's Changing?

We're splitting our monorepo into two focused repositories:

1. **HomeIQ Edge** (Public - this repo)
   - All on-premise components
   - Remains 100% open source (MIT License)
   - Works completely standalone

2. **HomeIQ Cloud** (Private)
   - AI/ML models trained on fleet data
   - SaaS infrastructure
   - Mobile apps

## Why This Change?

**For Open Source Users:**
- ✅ Clearer focus on edge-only use cases
- ✅ Easier to contribute (less complexity)
- ✅ Faster development of local features
- ✅ No confusion about what runs locally vs cloud

**For Cloud Users:**
- ✅ Better AI models (faster iteration)
- ✅ More robust SaaS features
- ✅ Improved mobile apps

**For Everyone:**
- ✅ Transparent about what code is open vs proprietary
- ✅ Clear separation of concerns
- ✅ Better documentation for each use case

## What's NOT Changing?

- ❌ Edge functionality remains the same
- ❌ Still works 100% locally without cloud
- ❌ Still MIT licensed
- ❌ Still accepting community contributions
- ❌ Cloud is still optional

## Timeline

- **Week of Nov 11:** Create new repo structure
- **Week of Nov 18:** Migrate cloud components
- **Week of Nov 25:** Update documentation
- **Dec 1:** Complete transition

## For Contributors

If you have open PRs, they'll be migrated automatically. No action needed!

## Questions?

Drop them below and I'll answer everything! 🙌

---

*This change reflects our commitment to both open source transparency AND building a sustainable business to support ongoing development.*
```

### Update Website & Documentation

Update all references from single repo to dual-repo model:
- Marketing website
- Documentation site
- README badges
- CI/CD workflows
- Package references

---

## New Files to Create

### Public Repository Files

1. **`homeiq-edge/docs/CONTRIBUTING.md`** - Contribution guidelines
2. **`homeiq-edge/docs/CODE_OF_CONDUCT.md`** - Community standards
3. **`homeiq-edge/docs/SECURITY.md`** - Security policy & disclosure
4. **`homeiq-edge/docs/PRIVACY.md`** - Privacy policy (created above)
5. **`homeiq-edge/addon/config.yaml`** - HA Add-on config (created above)
6. **`homeiq-edge/addon/Dockerfile`** - HA Add-on build (created above)
7. **`homeiq-edge/addon/run.sh`** - HA Add-on startup (created above)
8. **`homeiq-edge/cloud-sync/sync_agent.py`** - Sync agent (created above)
9. **`homeiq-edge/cloud-sync/telemetry_collector.py`** - Telemetry (created above)
10. **`homeiq-edge/cloud-sync/privacy_controls.py`** - Privacy controls (created above)
11. **`homeiq-edge/cloud-sync/encryption.py`** - Encryption (created above)
12. **`homeiq-edge/.github/ISSUE_TEMPLATE/`** - Issue templates
13. **`homeiq-edge/.github/PULL_REQUEST_TEMPLATE.md`** - PR template

### Private Repository Files

1. **`homeiq-cloud/README.md`** - Private repo README (created above)
2. **`homeiq-cloud/docs/ARCHITECTURE.md`** - Cloud architecture
3. **`homeiq-cloud/docs/DEPLOYMENT.md`** - Deployment procedures
4. **`homeiq-cloud/docs/ML_MODELS.md`** - Model documentation
5. **`homeiq-cloud/docs/API_INTERNAL.md`** - Internal API docs
6. **`homeiq-cloud/.github/workflows/`** - CI/CD for cloud
7. **`homeiq-cloud/infrastructure/terraform/`** - Infrastructure as code
8. **`homeiq-cloud/infrastructure/kubernetes/`** - K8s configs

---

## Testing & Validation

### Validate HomeIQ Remains Healthy

```bash
# Verify original HomeIQ is untouched and working
cd ~/projects/HomeIQ

# Check git status
git status  # Should show "nothing to commit, working tree clean"

# Verify services work
docker-compose up -d
./scripts/test-services.sh

# All tests should pass as before
```

### Test HomeIQ-Box Independently

```bash
# Test the new public repo works standalone
cd ~/projects/homeiq-box

# Build and start
docker-compose build
docker-compose up -d

# Verify all services start
docker-compose ps  # All should be "Up"

# Test end-to-end workflows
./scripts/test-services.sh

# Test HA Add-on (if implemented)
# Install in Home Assistant and verify functionality
```

### Test HomeIQ-Cloud (Dev Environment)

```bash
# Test cloud services locally
cd ~/projects/homeiq-cloud

# Start dev environment
docker-compose -f docker-compose.dev.yml up -d

# Verify services start
docker-compose ps

# Test API endpoints
curl http://localhost:8080/health
```

### Integration Testing (Box ↔ Cloud)

```bash
# Test edge → cloud communication

# 1. Start cloud services
cd ~/projects/homeiq-cloud
docker-compose -f docker-compose.dev.yml up -d

# 2. Configure box to connect to local cloud
cd ~/projects/homeiq-box
export CLOUD_SYNC_ENABLED=true
export CLOUD_API_URL=http://localhost:8080
export CLOUD_API_KEY=test-key

# 3. Start box
docker-compose up -d

# 4. Verify sync works
docker logs homeiq_cloud_sync --tail=100
# Look for "Telemetry sent successfully"

# 5. Verify data received in cloud
cd ~/projects/homeiq-cloud
docker logs data-lake-ingestion --tail=100
# Look for incoming telemetry
```

### Validation Checklist

**HomeIQ (Original):**
- [ ] Git status clean, no changes
- [ ] All services start successfully
- [ ] Tests pass
- [ ] Documentation accessible
- [ ] Development continues normally

**HomeIQ-Box (New Public):**
- [ ] All edge services present and working
- [ ] HA Add-on config valid
- [ ] Cloud sync agent present
- [ ] Privacy documentation complete
- [ ] Can run standalone (no cloud needed)
- [ ] Can optionally sync to cloud
- [ ] README clear and helpful
- [ ] Build process works
- [ ] Tests pass

**HomeIQ-Cloud (New Private):**
- [ ] Cloud services structure created
- [ ] Can receive telemetry from box
- [ ] Infrastructure configs present
- [ ] Private README appropriate
- [ ] Team has access
- [ ] No edge code present

**Integration:**
- [ ] Box can sync to cloud (when enabled)
- [ ] Cloud receives and processes data
- [ ] Box works without cloud
- [ ] API compatibility maintained

---

## Timeline & Milestones

### Week 1: Preparation
- [ ] Day 1-2: Backup and audit
- [ ] Day 3-4: Create new repos
- [ ] Day 5: Plan communication

### Week 2: Split Execution
- [ ] Day 1-3: Create private repo
- [ ] Day 4-5: Update public repo
- [ ] Weekend: Initial testing

### Week 3: New Components
- [ ] Day 1-2: Create HA Add-on
- [ ] Day 3-4: Create cloud sync agent
- [ ] Day 5: Create privacy docs
- [ ] Weekend: Integration testing

### Week 4: Documentation & Launch
- [ ] Day 1-2: Update all docs
- [ ] Day 3: Community announcement
- [ ] Day 4-5: Support & Q&A
- [ ] Weekend: Monitor feedback

### Week 5: Refinement
- [ ] Address community feedback
- [ ] Fix any issues discovered
- [ ] Update CI/CD pipelines
- [ ] Complete migration

---

## Rollback Plan

Since HomeIQ remains unchanged, rollback is simple:

### If HomeIQ-Box Has Issues
```bash
# Simply continue using HomeIQ for development
cd ~/projects/HomeIQ
# Continue working as normal

# Fix issues in HomeIQ-Box
cd ~/projects/homeiq-box
# Fix bugs, update code
git commit -am "Fix issue"
git push

# No impact on HomeIQ repository
```

### If HomeIQ-Cloud Has Issues
```bash
# Cloud is private and separate
# No impact on HomeIQ or HomeIQ-Box

# Fix issues independently
cd ~/projects/homeiq-cloud
# Fix bugs, update code
```

### Complete Rollback (Worst Case)
```bash
# If you need to abandon the new repos entirely:

# 1. Archive them on GitHub
# Settings > General > Archive this repository

# 2. Continue development in HomeIQ
cd ~/projects/HomeIQ
# Business as usual

# 3. Try again later with lessons learned
```

**Key Advantage:** Since HomeIQ is untouched, there's zero risk to current operations.

---

## Success Criteria

The restructure is successful when:

**HomeIQ (Original):**
- [ ] Repository unchanged and healthy
- [ ] Development continues normally
- [ ] Team understands relationship to new repos
- [ ] README updated with note about HomeIQ-Box

**HomeIQ-Box (New Public):**
- [ ] Builds and deploys without errors
- [ ] All edge services function correctly
- [ ] HA Add-on installs and runs
- [ ] Cloud sync agent works (when enabled)
- [ ] Documentation complete and clear
- [ ] Community understands purpose
- [ ] No regressions in functionality
- [ ] GitHub Actions/CI working
- [ ] First 10 users successfully deploy

**HomeIQ-Cloud (New Private):**
- [ ] Repository created and secured
- [ ] Basic service structure in place
- [ ] Can receive telemetry from Box
- [ ] Team has appropriate access
- [ ] Development plan documented
- [ ] Infrastructure configs started

**Integration:**
- [ ] Box ↔ Cloud communication works
- [ ] API compatibility maintained
- [ ] Version sync strategy defined
- [ ] Testing pipeline established

**Communication:**
- [ ] Community announcement posted
- [ ] Documentation updated across all repos
- [ ] Team aligned on strategy
- [ ] Support channels ready

---

## Post-Restructure Maintenance

### Three-Repository Model

**HomeIQ (Development):**
- Active feature development
- Experimental code
- Internal testing
- Fast iteration
- May be unstable

**HomeIQ-Box (Production Edge):**
- Stable releases only
- Accept community contributions
- Regular security updates
- Bug fixes
- Documentation improvements
- New edge-only features

**HomeIQ-Cloud (Private SaaS):**
- Internal development only
- AI model improvements
- SaaS feature development
- Mobile app updates
- Business logic changes

### Development Flow

```
┌─────────────────────────────────────────────┐
│ New Feature Development                     │
│                                             │
│ HomeIQ (dev) → Test → Stabilize            │
│                           ↓                 │
│               Merge to HomeIQ-Box (release) │
│                           ↓                 │
│                   Users benefit             │
└─────────────────────────────────────────────┘
```

### Release Process

**For HomeIQ-Box:**
1. Develop feature in HomeIQ
2. Test thoroughly
3. Cherry-pick stable changes to HomeIQ-Box
4. Tag release in HomeIQ-Box
5. Announce to community

**For HomeIQ-Cloud:**
1. Develop internally
2. Deploy to staging
3. Test with Box integration
4. Deploy to production
5. Monitor metrics

### Version Compatibility

Maintain compatibility matrix:

| HomeIQ-Box | HomeIQ-Cloud | Status |
|------------|--------------|--------|
| v1.0.x     | v1.0.x       | ✅ Compatible |
| v1.1.x     | v1.0.x       | ⚠️ Degraded features |
| v1.0.x     | v1.1.x       | ✅ Compatible |

### API Versioning

- Box and Cloud communicate via versioned API
- `/v1/telemetry` - Current stable
- `/v2/telemetry` - Next version (beta)
- Maintain backwards compatibility for 6 months

---

## Conclusion

This restructuring strategy positions HomeIQ for success while minimizing risk:

### Key Benefits

**1. Zero Risk to Current Operations**
- HomeIQ repository remains unchanged
- Development continues uninterrupted
- No chance of breaking existing functionality
- Can rollback easily if needed

**2. Clear Product Structure**
```
HomeIQ (dev) → Fast iteration, experimental
    ↓
HomeIQ-Box (prod) → Stable, open source, community
    ↓
HomeIQ-Cloud (optional) → Premium features, revenue
```

**3. Community Trust**
- Open-source edge builds credibility
- Transparent about data collection
- Users can audit what runs in their home
- Optional cloud features (not forced)

**4. Competitive Advantage**
- AI models trained on fleet data = moat
- Cloud infrastructure proprietary
- Can iterate quickly without exposing strategy

**5. Business Model Clarity**
- Free tier: HomeIQ-Box (open source)
- Paid tier: HomeIQ-Box + Cloud subscription
- Hardware option: NUC with Box pre-installed

### Risk Mitigation

✅ **HomeIQ untouched** - zero disruption  
✅ **Copy, don't move** - always have source  
✅ **Test independently** - each repo validated  
✅ **Gradual rollout** - soft launch before announcement  
✅ **Easy rollback** - archive new repos if needed  

### Next Steps

1. **Review this guide** - Make sure you agree with the approach
2. **Week 1-2: Create HomeIQ-Box** - Copy and refine edge components
3. **Week 3: Create HomeIQ-Cloud** - Build cloud service structure
4. **Week 4: Test integration** - Ensure Box ↔ Cloud works
5. **Week 5: Soft launch** - Release to select users first
6. **Week 6+: Scale** - Announce publicly and grow

### Success Metrics

**Month 1:**
- [ ] HomeIQ-Box: 50 stars on GitHub
- [ ] 10 users deploy successfully
- [ ] Zero critical bugs

**Month 3:**
- [ ] 200+ stars on GitHub
- [ ] 100+ deployments
- [ ] 10+ code contributors
- [ ] 5 paying cloud customers

**Month 6:**
- [ ] 1,000+ stars
- [ ] 500+ deployments
- [ ] 50 paying cloud customers ($10k MRR)
- [ ] HomeIQ-Box referenced in HA community

### Long-term Vision

**Year 1:** Establish HomeIQ-Box as go-to HA data platform  
**Year 2:** 10,000 deployments, $100k MRR from cloud  
**Year 3:** Expand to commercial integrators (HomeIQ Pro)  

---

**The Bottom Line:** This three-repo structure lets you:
- Keep developing fast (HomeIQ)
- Build community trust (HomeIQ-Box)
- Create revenue (HomeIQ-Cloud)
- Minimize risk (nothing changes for current work)

This is the right architecture for a sustainable, growing business.

---

**Questions or Issues?**
- Internal: dev@homeiq.io
- Community: GitHub Discussions in respective repos
- Support: support@homeiq.io

**Document Version:** 2.1 (Three-Repo Model)  
**Last Updated:** November 13, 2025  
**Author:** HomeIQ Development Team
