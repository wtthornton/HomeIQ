# HomeIQ Frontend Terminology Guide

**Created:** 2026-02-25
**Purpose:** Ensure consistent language across all 3 frontend apps.
**Referenced by:** [Frontend Redesign Plan](./planning/frontend-redesign-plan.md) (Epic FR-5.3)

---

## Canonical Terms

Use these terms in all user-facing UI text (nav labels, headings, buttons, tooltips).

| Canonical Term | Use For | Do NOT Use |
|---|---|---|
| **Automations** | Live automations deployed to HA | "Deployed", "Deployed Automations" |
| **Ideas** | AI-generated automation suggestions (any source) | "Suggestions" (nav only — ok in body text), "Proactive Suggestions" |
| **Insights** | ML-detected patterns and cross-device opportunities | "Patterns" (standalone), "Synergies" |
| **Chat** | Conversational AI agent interface | "Agent", "HA Agent Chat", "HA AI Agent" |
| **Explore** | Device explorer and shopping recommendations | "Discovery", "Discovery Page" |
| **Devices** | Physical smart home devices (user-facing) | "Entities" (ok in API/code, not in UI text) |
| **Device Health** | Device naming quality and status | "Device Hygiene" |
| **Automation Checks** | HA automation validation results | "HA Validation" |
| **AI Performance** | Agent evaluation framework results | "Agent Evaluation" |
| **Data Feeds** | External data source status | "Data Sources" |
| **Performance** | Service health, latency, error rates | "Service Performance Monitoring" |
| **Live** | Real-time streaming and monitoring | "Real-Time Monitoring", "Real-Time Observability" |
| **Traces** | Distributed trace visualization | "Trace Visualization" |
| **HomeIQ** | App/product name | "HA AutomateAI" |

## Body Text vs. Nav Labels

- **Nav labels** should be one word when possible: "Ideas", "Chat", "Insights", "Automations"
- **Body text / subtitles** can use longer descriptions: "AI-generated automation ideas", "Your live automations"
- **Page titles** (`<title>` tag) use: "Ideas | HomeIQ", "Chat | HomeIQ", etc.

## Status Labels

Use consistently across all apps:

| Status | Label | Color Role |
|---|---|---|
| Healthy / OK / Running | "Healthy" | `--success` (green) |
| Warning / Degraded | "Warning" | `--warning` (amber) |
| Error / Critical / Down | "Error" | `--error` (red) |
| Informational / Neutral | "Info" | `--info` (sky blue) |
| Pending / Loading | "Pending" | `--text-muted` (grey) |

## App Names

| App | Short Name | Full Name | Used In |
|---|---|---|---|
| AI Automation UI | **HomeIQ** | HomeIQ — AI-Powered Smart Home Intelligence | Nav logo, footer, `<title>` |
| Health Dashboard | **HomeIQ Health** | HomeIQ Health Dashboard | Header, `<title>` |
| Observability Dashboard | **HomeIQ Ops** | HomeIQ Ops — Internal Observability | Streamlit title, sidebar |

## Emoji Policy

- **No emoji in nav labels** — use text only
- **No emoji in page headings** — use text only
- **Emoji OK in**: status indicators within data tables, toast notifications, informational banners
- **Prefer icons over emoji** when possible (line icon set TBD in FR-1.6)
