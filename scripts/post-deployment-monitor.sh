#!/bin/bash
# =============================================================================
# HomeIQ Post-Deployment Monitor (Phase 6)
# =============================================================================
# Continuous health check loop designed to run for 48 hours after deployment.
# Monitors all 50 services, tracks error rates, and alerts on threshold breaches.
#
# Usage:
#   ./scripts/post-deployment-monitor.sh                    # Run for 48 hours
#   ./scripts/post-deployment-monitor.sh --duration 4       # Run for 4 hours
#   ./scripts/post-deployment-monitor.sh --interval 120     # Check every 2 min
#   ./scripts/post-deployment-monitor.sh --alert-threshold 3 # Alert after 3 failures
#
# Output:
#   - Hourly summary to stdout and log file
#   - Alert on threshold breaches
#   - Final report on exit (Ctrl+C or duration reached)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export PROJECT_ROOT
source "$SCRIPT_DIR/deployment/common.sh"

# Defaults
DURATION_HOURS=${DURATION_HOURS:-48}
CHECK_INTERVAL=${CHECK_INTERVAL:-60}       # seconds between checks
ALERT_THRESHOLD=${ALERT_THRESHOLD:-3}      # consecutive failures before alert
HOURLY_SUMMARY_INTERVAL=3600               # 1 hour in seconds

while [[ $# -gt 0 ]]; do
  case $1 in
    --duration)          DURATION_HOURS="$2"; shift 2 ;;
    --interval)          CHECK_INTERVAL="$2"; shift 2 ;;
    --alert-threshold)   ALERT_THRESHOLD="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: $0 [--duration HOURS] [--interval SECONDS] [--alert-threshold N]"
      echo "  --duration N          Run for N hours (default: 48)"
      echo "  --interval N          Check every N seconds (default: 60)"
      echo "  --alert-threshold N   Alert after N consecutive failures (default: 3)"
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# Override log file for monitoring
LOG_FILE="${LOG_DIR}/monitor_${DEPLOY_TIMESTAMP}.log"

# All services to monitor (name:port:endpoint)
ALL_SERVICES=(
  # Tier 1 — Critical
  "websocket-ingestion:8001:/health"
  "data-api:8006:/health"
  "admin-api:8004:/health"
  # Tier 2 — Essential
  "health-dashboard:3000:/health"
  "data-retention:8080:/health"
  "weather-api:8009:/health"
  "smart-meter-service:8014:/health"
  "sports-api:8005:/health"
  "calendar-service:8013:/health"
  "carbon-intensity:8010:/health"
  "electricity-pricing:8011:/health"
  "air-quality:8012:/health"
  "log-aggregator:8015:/health"
  # Tier 3 — ML/AI
  "openvino-service:8026:/health"
  "ml-service:8025:/health"
  "ai-core-service:8018:/health"
  "ai-training-service:8033:/health"
  "device-intelligence-service:8028:/health"
  "rag-service:8027:/health"
  "openai-service:8020:/health"
  # Tier 4 — Automation Core
  "ha-ai-agent-service:8030:/health"
  "ai-automation-service-new:8036:/health"
  "ai-query-service:8035:/health"
  "yaml-validation-service:8037:/health"
  "automation-linter:8016:/health"
  "automation-trace-service:8044:/health"
  # Tier 5 — Blueprints
  "blueprint-index:8038:/health"
  "blueprint-suggestion-service:8039:/health"
  "rule-recommendation-ml:8040:/api/v1/health"
  "automation-miner:8029:/health"
  # Tier 6 — Energy Analytics
  "energy-correlator:8017:/health"
  "energy-forecasting:8042:/api/v1/health"
  "proactive-agent-service:8031:/health"
  # Tier 7 — Device Management
  "device-health-monitor:8019:/health"
  "device-context-classifier:8032:/health"
  "device-setup-assistant:8021:/health"
  "device-database-client:8022:/health"
  "device-recommender:8023:/health"
  "activity-writer:8045:/health"
  "ha-setup-service:8024:/health"
  # Tier 8 — Pattern Analysis
  "ai-pattern-service:8034:/health"
  "api-automation-edge:8041:/health"
  # Tier 9 — Frontends
  "jaeger:16686:/"
  "observability-dashboard:8501:/_stcore/health"
  "ai-automation-ui:3001:/health"
  # Infrastructure
  "influxdb:8086:/health"
  "prometheus:9090:/-/healthy"
  "grafana:3002:/api/health"
)

# Tracking
declare -A CONSECUTIVE_FAILURES
declare -A TOTAL_FAILURES
declare -A TOTAL_CHECKS_PER_SERVICE
TOTAL_ROUNDS=0
TOTAL_ALERTS=0
MONITOR_START=$(date +%s)
LAST_HOURLY=$(date +%s)

# Initialize counters
for entry in "${ALL_SERVICES[@]}"; do
  IFS=':' read -r name _ _ <<< "$entry"
  CONSECUTIVE_FAILURES[$name]=0
  TOTAL_FAILURES[$name]=0
  TOTAL_CHECKS_PER_SERVICE[$name]=0
done

# --- Alert function ---
fire_alert() {
  local service=$1
  local port=$2
  local consecutive=$3
  TOTAL_ALERTS=$((TOTAL_ALERTS + 1))

  echo "" | tee -a "$LOG_FILE"
  log_error "ALERT: $service (port $port) has failed $consecutive consecutive health checks"
  log_error "  Investigate: docker logs $(docker ps --filter "publish=$port" --format '{{.Names}}' 2>/dev/null || echo 'unknown')"
  log_error "  Restart:     docker compose -f domains/*/compose.yml up -d <service>"
  echo "" | tee -a "$LOG_FILE"
}

# --- Hourly summary ---
print_hourly_summary() {
  local now=$(date +%s)
  local elapsed_hours=$(( (now - MONITOR_START) / 3600 ))
  local total_services=${#ALL_SERVICES[@]}

  # Count currently healthy
  local healthy_now=0
  for entry in "${ALL_SERVICES[@]}"; do
    IFS=':' read -r name port endpoint <<< "$entry"
    if curl -f -s --max-time 3 "http://localhost:${port}${endpoint}" > /dev/null 2>&1; then
      healthy_now=$((healthy_now + 1))
    fi
  done

  # Count services with any failures
  local services_with_failures=0
  for entry in "${ALL_SERVICES[@]}"; do
    IFS=':' read -r name _ _ <<< "$entry"
    if [ "${TOTAL_FAILURES[$name]}" -gt 0 ]; then
      services_with_failures=$((services_with_failures + 1))
    fi
  done

  echo "" | tee -a "$LOG_FILE"
  log_info "--- HOURLY SUMMARY (Hour $elapsed_hours) ---"
  log_info "  Services healthy:     $healthy_now/$total_services"
  log_info "  Check rounds:         $TOTAL_ROUNDS"
  log_info "  Services w/ failures: $services_with_failures"
  log_info "  Total alerts fired:   $TOTAL_ALERTS"

  # List any currently unhealthy services
  if [ $healthy_now -lt $total_services ]; then
    log_warn "  Currently unhealthy services:"
    for entry in "${ALL_SERVICES[@]}"; do
      IFS=':' read -r name port endpoint <<< "$entry"
      if ! curl -f -s --max-time 3 "http://localhost:${port}${endpoint}" > /dev/null 2>&1; then
        log_warn "    - $name (port $port) — consecutive failures: ${CONSECUTIVE_FAILURES[$name]}"
      fi
    done
  fi

  log_info "--- END HOURLY SUMMARY ---"
  echo "" | tee -a "$LOG_FILE"
}

# --- Cleanup on exit ---
print_final_report() {
  local now=$(date +%s)
  local elapsed=$((now - MONITOR_START))
  local total_services=${#ALL_SERVICES[@]}

  echo "" | tee -a "$LOG_FILE"
  log_header "POST-DEPLOYMENT MONITORING FINAL REPORT"
  log_info "Duration:           $(format_duration $elapsed)"
  log_info "Check rounds:       $TOTAL_ROUNDS"
  log_info "Total alerts:       $TOTAL_ALERTS"
  echo "" | tee -a "$LOG_FILE"

  log_info "Per-service failure summary:"
  for entry in "${ALL_SERVICES[@]}"; do
    IFS=':' read -r name _ _ <<< "$entry"
    local fails=${TOTAL_FAILURES[$name]}
    local checks=${TOTAL_CHECKS_PER_SERVICE[$name]}
    if [ "$checks" -gt 0 ]; then
      local success_rate=$(( (checks - fails) * 100 / checks ))
      if [ "$fails" -gt 0 ]; then
        log_warn "  $name: $fails failures / $checks checks (${success_rate}% uptime)"
      else
        log_success "  $name: 0 failures / $checks checks (100% uptime)"
      fi
    fi
  done

  echo "" | tee -a "$LOG_FILE"
  if [ $TOTAL_ALERTS -eq 0 ]; then
    log_success "RESULT: Clean monitoring period — no alerts triggered"
  else
    log_warn "RESULT: $TOTAL_ALERTS alerts triggered during monitoring"
  fi
  log_info "Full log: $LOG_FILE"
}

trap print_final_report EXIT

# --- Main monitoring loop ---
log_header "HomeIQ Post-Deployment Monitor"
log_info "Duration:        ${DURATION_HOURS} hours"
log_info "Check interval:  ${CHECK_INTERVAL} seconds"
log_info "Alert threshold: ${ALERT_THRESHOLD} consecutive failures"
log_info "Services:        ${#ALL_SERVICES[@]}"
log_info "Log file:        $LOG_FILE"
log_info "Press Ctrl+C to stop and print final report"
echo ""

MONITOR_END=$((MONITOR_START + DURATION_HOURS * 3600))

while [ "$(date +%s)" -lt "$MONITOR_END" ]; do
  TOTAL_ROUNDS=$((TOTAL_ROUNDS + 1))
  local_healthy=0
  local_total=${#ALL_SERVICES[@]}

  for entry in "${ALL_SERVICES[@]}"; do
    IFS=':' read -r name port endpoint <<< "$entry"
    TOTAL_CHECKS_PER_SERVICE[$name]=$(( ${TOTAL_CHECKS_PER_SERVICE[$name]} + 1 ))

    if curl -f -s --max-time 5 "http://localhost:${port}${endpoint}" > /dev/null 2>&1; then
      # Reset consecutive failures on success
      CONSECUTIVE_FAILURES[$name]=0
      local_healthy=$((local_healthy + 1))
    else
      CONSECUTIVE_FAILURES[$name]=$(( ${CONSECUTIVE_FAILURES[$name]} + 1 ))
      TOTAL_FAILURES[$name]=$(( ${TOTAL_FAILURES[$name]} + 1 ))

      # Fire alert if threshold reached
      if [ "${CONSECUTIVE_FAILURES[$name]}" -eq "$ALERT_THRESHOLD" ]; then
        fire_alert "$name" "$port" "${CONSECUTIVE_FAILURES[$name]}"
      fi
    fi
  done

  # Brief status line
  remaining_hours=$(( (MONITOR_END - $(date +%s)) / 3600 ))
  remaining_mins=$(( ((MONITOR_END - $(date +%s)) % 3600) / 60 ))
  log_info "Round $TOTAL_ROUNDS: $local_healthy/$local_total healthy — ${remaining_hours}h ${remaining_mins}m remaining"

  # Hourly summary
  now=$(date +%s)
  if [ $((now - LAST_HOURLY)) -ge $HOURLY_SUMMARY_INTERVAL ]; then
    print_hourly_summary
    LAST_HOURLY=$now
  fi

  sleep "$CHECK_INTERVAL"
done

log_success "Monitoring period complete (${DURATION_HOURS} hours)"
