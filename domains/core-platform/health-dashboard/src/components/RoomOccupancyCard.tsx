/**
 * RoomOccupancyCard — per-room presence widget (TAP-7587).
 *
 * Fetches GET /api/status/rooms through the dashboard's own nginx proxy
 * (see health-dashboard/nginx.conf's `location /api/status/rooms` block) —
 * one entry per area known to data-api, including a zero-sensor area
 * reported "unknown" rather than omitted.
 */

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { useRoomOccupancy, RoomOccupancy } from '../hooks/useRoomOccupancy';

const stateBadge = (state: RoomOccupancy['state']): 'healthy' | 'secondary' | 'outline' => {
  switch (state) {
    case 'detected':
      return 'healthy' as const;
    case 'clear':
      return 'secondary' as const;
    default:
      return 'outline' as const;
  }
};

const areaLabel = (areaId: string): string => areaId.replace(/_/g, ' ');

export const RoomOccupancyCard: React.FC = () => {
  const { rooms, loading, error } = useRoomOccupancy();

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-semibold">Room Occupancy</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        {loading && !rooms && (
          <p className="text-sm text-muted-foreground">Loading room occupancy...</p>
        )}
        {error && <p className="text-sm text-status-critical">{error}</p>}
        {rooms && rooms.length === 0 && (
          <p className="text-sm text-muted-foreground">No known areas yet.</p>
        )}
        {rooms && rooms.length > 0 && (
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {rooms.map((room) => (
              <div key={room.area_id} className="rounded bg-muted/50 px-2 py-1.5">
                <div className="flex items-center justify-between">
                  <span className="truncate capitalize">{areaLabel(room.area_id)}</span>
                  <Badge variant={stateBadge(room.state)} size="sm">
                    {room.state}
                  </Badge>
                </div>
                {room.contributing_entity_ids.length > 0 && (
                  <p className="mt-1 truncate text-xs text-muted-foreground">
                    {room.contributing_entity_ids.join(', ')}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default React.memo(RoomOccupancyCard);
