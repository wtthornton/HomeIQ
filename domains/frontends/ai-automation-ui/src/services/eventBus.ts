/**
 * Real-time house status event bus via WebSocket.
 *
 * Connects to the websocket-ingestion `/ws/status` endpoint and
 * provides a subscribe/unsubscribe API for UI components that need
 * live house status updates.
 */

import type {
  HouseStatus,
  HouseStatusMessage,
} from '../types/houseStatus';

type Callback = (data: unknown) => void;

export class HouseStatusEventBus {
  private ws: WebSocket | null = null;
  private listeners: Map<string, Set<Callback>> = new Map();
  private reconnectDelay = 1000;
  private maxReconnectDelay = 30000;
  private currentStatus: HouseStatus | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private wsUrl = '';

  // -- connection lifecycle --------------------------------------------------

  /** Open a WebSocket connection with auto-reconnect. */
  connect(wsUrl: string): void {
    this.wsUrl = wsUrl;
    this.reconnectDelay = 1000;
    this._open();
  }

  /** Gracefully close the connection and stop reconnecting. */
  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.onclose = null; // prevent reconnect on intentional close
      this.ws.close();
      this.ws = null;
    }
  }

  // -- public API ------------------------------------------------------------

  /**
   * Subscribe to updates for a specific section (e.g. "climate",
   * "presence", "lights_by_area", "sensors", "switches_on",
   * "active_automations") or "*" for all deltas.
   *
   * Returns an unsubscribe function.
   */
  subscribe(section: string, callback: Callback): () => void {
    if (!this.listeners.has(section)) {
      this.listeners.set(section, new Set());
    }
    this.listeners.get(section)!.add(callback);
    return () => {
      this.listeners.get(section)?.delete(callback);
    };
  }

  /** Return the latest cached full snapshot (or null before first connect). */
  getStatus(): HouseStatus | null {
    return this.currentStatus;
  }

  // -- internal --------------------------------------------------------------

  private _open(): void {
    if (!this.wsUrl) return;
    try {
      this.ws = new WebSocket(this.wsUrl);
    } catch {
      this._scheduleReconnect();
      return;
    }

    this.ws.onmessage = (event: MessageEvent) => {
      try {
        const msg: HouseStatusMessage = JSON.parse(event.data as string);
        this._handleMessage(msg);
      } catch {
        // ignore malformed messages
      }
    };

    this.ws.onopen = () => {
      this.reconnectDelay = 1000; // reset backoff on success
      this._emit('_connected', null);
    };

    this.ws.onclose = () => {
      this._emit('_disconnected', null);
      this._scheduleReconnect();
    };

    this.ws.onerror = () => {
      // onclose will fire after onerror — reconnect happens there
    };
  }

  private _handleMessage(msg: HouseStatusMessage): void {
    if (msg.type === 'ping') return; // keepalive — no action needed

    if (msg.type === 'snapshot') {
      // Full snapshot — replace cached state.
      const { type: _t, ...rest } = msg;
      this.currentStatus = rest as HouseStatus;
      this._emit('*', this.currentStatus);
      // Also emit per-section so section-specific listeners fire.
      for (const section of Object.keys(rest)) {
        if (section !== 'timestamp') {
          this._emit(section, (rest as Record<string, unknown>)[section]);
        }
      }
      return;
    }

    if (msg.type === 'delta') {
      // Delta — update cached state and notify.
      if (this.currentStatus && msg.section) {
        (this.currentStatus as unknown as Record<string, unknown>)[msg.section] = msg.data;
        this.currentStatus.timestamp = new Date().toISOString();
      }
      this._emit(msg.section, msg.data);
      this._emit('*', this.currentStatus);
    }
  }

  private _emit(section: string, data: unknown): void {
    const cbs = this.listeners.get(section);
    if (cbs) {
      for (const cb of cbs) {
        try {
          cb(data);
        } catch {
          // don't let a bad listener break the bus
        }
      }
    }
  }

  private _scheduleReconnect(): void {
    if (this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.reconnectDelay = Math.min(
        this.reconnectDelay * 2,
        this.maxReconnectDelay,
      );
      this._open();
    }, this.reconnectDelay);
  }
}

/** Singleton instance for app-wide use. */
export const houseStatus = new HouseStatusEventBus();
