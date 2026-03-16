# Story 66.5 -- Health Dashboard AI Tier Badges

<!-- docsmcp:start:user-story -->

> **As a** operator, **I want** AI tier badges visible on service inventory cards in the health dashboard, **so that** I can see at a glance which services use LLMs or ML without checking docs

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 2 | **Size:** M

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that operators can see AI tier classifications at a glance on the health dashboard without consulting documentation.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

Add AI tier badges (True Agent, LLM, ML, Non-AI) to the service inventory cards in health-dashboard. Source tier data from a static JSON manifest generated from the classification doc.

See [Epic 66](stories/epic-66-ai-agent-classification.md) for project context and shared definitions.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/core-platform/health-dashboard/public/ai-tier-manifest.json`
- `domains/core-platform/health-dashboard/src/components/AiTierBadge.tsx`

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Create ai-tier-manifest.json with all 51 services (`domains/core-platform/health-dashboard/public/ai-tier-manifest.json`)
- [ ] Create AiTierBadge component (`domains/core-platform/health-dashboard/src/components/AiTierBadge.tsx`)
- [ ] Integrate badge into service inventory cards (`domains/core-platform/health-dashboard/src/components/services/ServiceCard.tsx`)
- [ ] Write tests for badge component (`domains/core-platform/health-dashboard/src/components/__tests__/AiTierBadge.test.tsx`)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Each service card shows an AI tier badge
- [ ] Badges use distinct colors per tier
- [ ] Tier data sourced from static JSON manifest
- [ ] Badge tooltip shows model/framework details

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 66](stories/epic-66-ai-agent-classification.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

1. `test_ac1_each_service_card_shows_ai_tier_badge` -- Each service card shows an AI tier badge
2. `test_ac2_badges_use_distinct_colors_per_tier` -- Badges use distinct colors per tier
3. `test_ac3_tier_data_sourced_from_static_json_manifest` -- Tier data sourced from static JSON manifest
4. `test_ac4_badge_tooltip_shows_modelframework_details` -- Badge tooltip shows model/framework details

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Document implementation hints, API contracts, data formats...

### Expert Recommendations

- **Security Expert** (70%): *Senior application security architect specializing in OWASP, threat modeling, and secure-by-default design.*
- **Software Architecture Expert** (62%): *Principal software architect focused on clean architecture, domain-driven design, and evolutionary system design.*

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- List stories or external dependencies that must complete first...

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [x] **I**ndependent -- Can be developed and delivered independently
- [ ] **N**egotiable -- Details can be refined during implementation
- [x] **V**aluable -- Delivers value to a user or the system
- [x] **E**stimable -- Team can estimate the effort
- [x] **S**mall -- Completable within one sprint/iteration
- [x] **T**estable -- Has clear criteria to verify completion

<!-- docsmcp:end:invest -->
