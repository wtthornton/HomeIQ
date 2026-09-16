import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '../../tests/test-utils';

import { RoomOccupancyCard } from '../RoomOccupancyCard';
import { useRoomOccupancy, RoomOccupancy } from '../../hooks/useRoomOccupancy';

vi.mock('../../hooks/useRoomOccupancy');

const mockUseRoomOccupancy = vi.mocked(useRoomOccupancy);

// VAL-04 fixture: 2 areas x 2 sensors each = 4 sensor ids, one area
// "detected", one "clear" — both must render, with all four ids visible.
const twoAreasFourSensors: RoomOccupancy[] = [
  {
    area_id: 'office',
    state: 'detected',
    contributing_entity_ids: ['binary_sensor.office_motion', 'binary_sensor.office_occupancy'],
    last_changed: '2026-09-15T00:00:00+00:00',
  },
  {
    area_id: 'kitchen',
    state: 'clear',
    contributing_entity_ids: ['binary_sensor.kitchen_motion', 'binary_sensor.kitchen_occupancy'],
    last_changed: '2026-09-15T00:00:00+00:00',
  },
];

describe('RoomOccupancyCard', () => {
  it('renders both areas and all four contributing sensor ids from the fixture', () => {
    mockUseRoomOccupancy.mockReturnValue({
      rooms: twoAreasFourSensors,
      loading: false,
      error: null,
    });

    render(<RoomOccupancyCard />);

    expect(screen.getByText('office')).toBeTruthy();
    expect(screen.getByText('kitchen')).toBeTruthy();
    expect(screen.getByText('detected')).toBeTruthy();
    expect(screen.getByText('clear')).toBeTruthy();
    expect(screen.getByText(/binary_sensor\.office_motion/)).toBeTruthy();
    expect(screen.getByText(/binary_sensor\.office_occupancy/)).toBeTruthy();
    expect(screen.getByText(/binary_sensor\.kitchen_motion/)).toBeTruthy();
    expect(screen.getByText(/binary_sensor\.kitchen_occupancy/)).toBeTruthy();
  });

  it('shows a zero-sensor area as "unknown" with no contributing sensors listed', () => {
    mockUseRoomOccupancy.mockReturnValue({
      rooms: [
        {
          area_id: 'guest_room',
          state: 'unknown',
          contributing_entity_ids: [],
          last_changed: '',
        },
      ],
      loading: false,
      error: null,
    });

    render(<RoomOccupancyCard />);

    expect(screen.getByText(/guest room/i)).toBeTruthy();
    expect(screen.getByText('unknown')).toBeTruthy();
  });

  it('renders no per-room view for an empty rooms payload', () => {
    mockUseRoomOccupancy.mockReturnValue({
      rooms: [],
      loading: false,
      error: null,
    });

    render(<RoomOccupancyCard />);

    expect(screen.queryByText(/office/i)).toBeNull();
    expect(screen.queryByText(/kitchen/i)).toBeNull();
    expect(screen.getByText(/No known areas yet/i)).toBeTruthy();
  });

  it('exposes the full contributing sensor list for a room with four long entity ids', () => {
    const longIds = [
      'binary_sensor.living_room_south_wall_motion_sensor_occupancy',
      'binary_sensor.living_room_north_wall_motion_sensor_occupancy',
      'binary_sensor.living_room_ceiling_mounted_presence_sensor',
      'binary_sensor.living_room_east_window_motion_sensor_occupancy',
    ];
    mockUseRoomOccupancy.mockReturnValue({
      rooms: [
        {
          area_id: 'living_room',
          state: 'detected',
          contributing_entity_ids: longIds,
          last_changed: '2026-09-15T00:00:00+00:00',
        },
      ],
      loading: false,
      error: null,
    });

    render(<RoomOccupancyCard />);

    const list = screen.getByTitle(longIds.join(', '));
    for (const id of longIds) {
      expect(list.getAttribute('title')).toContain(id);
    }

    expect(list.className).not.toMatch(/\btruncate\b/);
    for (const id of longIds) {
      expect(list.textContent).toContain(id);
    }
  });

  it('shows an error message when the fetch fails', () => {
    mockUseRoomOccupancy.mockReturnValue({
      rooms: null,
      loading: false,
      error: 'HTTP 503: Service Unavailable',
    });

    render(<RoomOccupancyCard />);

    expect(screen.getByText(/HTTP 503/)).toBeTruthy();
  });
});
