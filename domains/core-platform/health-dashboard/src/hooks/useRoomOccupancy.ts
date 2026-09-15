import { useState, useEffect } from 'react';

// Mirrors house_status/models.py's RoomOccupancy (TAP-7587).
export interface RoomOccupancy {
  area_id: string;
  state: 'detected' | 'clear' | 'unknown';
  contributing_entity_ids: string[];
  last_changed: string;
}

interface RoomsResponse {
  rooms: RoomOccupancy[];
}

// Plain fetch rather than the apiService/dataApi clients (services/api.ts):
// this route lives on websocket-ingestion, not admin-api or data-api, the
// two backends those clients are scoped to. HouseStatusCard.tsx (the other
// house_status consumer) makes the same choice for its WebSocket connection.
// The relative path is resolved by the browser against the current origin,
// so nginx's `/api/status/rooms` location (health-dashboard/nginx.conf)
// proxies it to websocket-ingestion with the bearer token injected —
// the key never ships in this bundle.
const ROOMS_URL = '/api/status/rooms';

interface UseRoomOccupancyResult {
  rooms: RoomOccupancy[] | null;
  loading: boolean;
  error: string | null;
}

export const useRoomOccupancy = (refreshInterval: number = 30000): UseRoomOccupancyResult => {
  const [rooms, setRooms] = useState<RoomOccupancy[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    const controller = new AbortController();

    const fetchRooms = async (): Promise<void> => {
      try {
        const response = await fetch(ROOMS_URL, { signal: controller.signal });
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const data: RoomsResponse = await response.json();
        if (mounted) {
          setRooms(data.rooms);
          setError(null);
        }
      } catch (err) {
        if (mounted && !controller.signal.aborted) {
          setError(err instanceof Error ? err.message : 'Failed to fetch room occupancy');
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    fetchRooms();
    const interval = setInterval(fetchRooms, refreshInterval);

    return () => {
      mounted = false;
      controller.abort();
      clearInterval(interval);
    };
  }, [refreshInterval]);

  return { rooms, loading, error };
};
