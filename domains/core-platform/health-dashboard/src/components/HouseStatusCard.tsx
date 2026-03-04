/**
 * HouseStatusCard — Real-time house status widget.
 *
 * Connects to the websocket-ingestion /ws/status endpoint and displays
 * a live summary of climate, presence, lights, sensors, switches, and
 * active automations.
 *
 * Epic 28 — Story 28.3
 */

import React, { useEffect, useState, useCallback, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';

// ---------- Types (mirrored from house_status/models.py) ----------

interface ClimateStatus {
  entity_id: string;
  friendly_name: string;
  current_temperature: number | null;
  target_temperature: number | null;
  hvac_mode: string;
  unit: string;
}

interface PresenceStatus {
  name: string;
  state: string;
}

interface AreaLightStatus {
  area: string;
  on_count: number;
  off_count: number;
}

interface SensorStatus {
  name: string;
  state: string;
  device_class: string;
}

interface HouseStatus {
  climate: ClimateStatus[];
  presence: PresenceStatus[];
  lights_by_area: AreaLightStatus[];
  sensors: Record<string, SensorStatus[]>;
  switches_on: string[];
  active_automations: string[];
  timestamp: string;
}

// ---------- Helpers ----------

const WS_BASE = import.meta.env.VITE_WS_INGESTION_URL || 'ws://localhost:8001';

const presenceBadge = (state: string) => {
  switch (state) {
    case 'home':
      return 'healthy' as const;
    case 'not_home':
      return 'warning' as const;
    default:
      return 'secondary' as const;
  }
};

const tempColor = (temp: number | null): string => {
  if (temp === null) return 'text-muted-foreground';
  if (temp < 16) return 'text-blue-500';
  if (temp < 22) return 'text-teal-500';
  if (temp < 26) return 'text-amber-500';
  return 'text-red-500';
};

// ---------- Component ----------

export const HouseStatusCard: React.FC = () => {
  const [status, setStatus] = useState<HouseStatus | null>(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const delayRef = useRef(1000);

  const connect = useCallback(() => {
    const ws = new WebSocket(`${WS_BASE}/ws/status`);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      delayRef.current = 1000;
    };

    ws.onmessage = (event: MessageEvent) => {
      try {
        const msg = JSON.parse(event.data as string);
        if (msg.type === 'snapshot') {
          const { type: _t, ...rest } = msg;
          setStatus(rest as HouseStatus);
        } else if (msg.type === 'delta' && msg.section) {
          setStatus((prev) => {
            if (!prev) return prev;
            return {
              ...prev,
              [msg.section]: msg.data,
              timestamp: new Date().toISOString(),
            };
          });
        }
        // ping — ignore
      } catch {
        // ignore malformed
      }
    };

    ws.onclose = () => {
      setConnected(false);
      reconnectRef.current = setTimeout(() => {
        delayRef.current = Math.min(delayRef.current * 2, 30000);
        connect();
      }, delayRef.current);
    };

    ws.onerror = () => {
      // onclose fires after — reconnect handled there
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
    };
  }, [connect]);

  // ---------- Render ----------

  if (!status) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base font-semibold flex items-center gap-2">
            House Status
            <Badge variant={connected ? 'healthy' : 'critical'} size="sm">
              {connected ? 'connecting' : 'offline'}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Waiting for data...</p>
        </CardContent>
      </Card>
    );
  }

  const openDoors = (status.sensors['door'] || []).filter(
    (s) => s.state === 'open',
  );
  const openWindows = (status.sensors['window'] || []).filter(
    (s) => s.state === 'open',
  );
  const motionDetected = (status.sensors['motion'] || []).filter(
    (s) => s.state === 'detected',
  );

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-semibold flex items-center gap-2">
          House Status
          <Badge variant={connected ? 'healthy' : 'critical'} size="sm">
            {connected ? 'live' : 'offline'}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        {/* Climate */}
        {status.climate.length > 0 && (
          <section>
            <h4 className="font-medium text-muted-foreground mb-1">Climate</h4>
            <div className="grid grid-cols-2 gap-2">
              {status.climate.map((c) => (
                <div
                  key={c.entity_id}
                  className="flex items-center justify-between rounded bg-muted/50 px-2 py-1"
                >
                  <span className="truncate">{c.friendly_name}</span>
                  <span className={`font-mono tabular-nums ${tempColor(c.current_temperature)}`}>
                    {c.current_temperature !== null
                      ? `${c.current_temperature}\u00B0${c.unit}`
                      : '--'}
                  </span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Presence */}
        {status.presence.length > 0 && (
          <section>
            <h4 className="font-medium text-muted-foreground mb-1">Presence</h4>
            <div className="flex flex-wrap gap-2">
              {status.presence.map((p) => (
                <Badge key={p.name} variant={presenceBadge(p.state)} size="sm">
                  {p.name}: {p.state === 'not_home' ? 'away' : p.state}
                </Badge>
              ))}
            </div>
          </section>
        )}

        {/* Lights */}
        {status.lights_by_area.length > 0 && (
          <section>
            <h4 className="font-medium text-muted-foreground mb-1">Lights</h4>
            <div className="grid grid-cols-2 gap-2">
              {status.lights_by_area.map((a) => (
                <div
                  key={a.area}
                  className="flex items-center justify-between rounded bg-muted/50 px-2 py-1"
                >
                  <span className="truncate capitalize">{a.area}</span>
                  <span className="font-mono tabular-nums">
                    {a.on_count > 0 ? (
                      <span className="text-amber-500">{a.on_count} on</span>
                    ) : (
                      <span className="text-muted-foreground">all off</span>
                    )}
                  </span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Alerts: open doors / windows */}
        {(openDoors.length > 0 || openWindows.length > 0) && (
          <section>
            <h4 className="font-medium text-muted-foreground mb-1">Alerts</h4>
            <div className="flex flex-wrap gap-2">
              {openDoors.map((s) => (
                <Badge key={s.name} variant="warning" size="sm">
                  {s.name}: open
                </Badge>
              ))}
              {openWindows.map((s) => (
                <Badge key={s.name} variant="warning" size="sm">
                  {s.name}: open
                </Badge>
              ))}
            </div>
          </section>
        )}

        {/* Motion */}
        {motionDetected.length > 0 && (
          <section>
            <h4 className="font-medium text-muted-foreground mb-1">Motion</h4>
            <div className="flex flex-wrap gap-2">
              {motionDetected.map((s) => (
                <Badge key={s.name} variant="healthy" size="sm">
                  {s.name}
                </Badge>
              ))}
            </div>
          </section>
        )}

        {/* Switches */}
        {status.switches_on.length > 0 && (
          <section>
            <h4 className="font-medium text-muted-foreground mb-1">
              Active Switches ({status.switches_on.length})
            </h4>
            <div className="flex flex-wrap gap-1">
              {status.switches_on.slice(0, 10).map((s) => (
                <Badge key={s} variant="secondary" size="sm">
                  {s.replace('switch.', '')}
                </Badge>
              ))}
              {status.switches_on.length > 10 && (
                <Badge variant="secondary" size="sm">
                  +{status.switches_on.length - 10} more
                </Badge>
              )}
            </div>
          </section>
        )}

        {/* Active automations */}
        {status.active_automations.length > 0 && (
          <section>
            <h4 className="font-medium text-muted-foreground mb-1">
              Active Automations ({status.active_automations.length})
            </h4>
            <div className="flex flex-wrap gap-1">
              {status.active_automations.slice(0, 8).map((a) => (
                <Badge key={a} variant="secondary" size="sm">
                  {a.replace('automation.', '')}
                </Badge>
              ))}
              {status.active_automations.length > 8 && (
                <Badge variant="secondary" size="sm">
                  +{status.active_automations.length - 8} more
                </Badge>
              )}
            </div>
          </section>
        )}

        {/* Timestamp */}
        <p className="text-xs text-muted-foreground text-right">
          Updated: {new Date(status.timestamp).toLocaleTimeString()}
        </p>
      </CardContent>
    </Card>
  );
};

export default React.memo(HouseStatusCard);
