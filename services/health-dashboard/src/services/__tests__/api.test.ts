import { describe, it, expect, vi, afterEach } from 'vitest';
import { apiService } from '../api';
import type { ServicesHealthResponse } from '../../types/health';

const mockServicesHealth: ServicesHealthResponse = {
  'weather-api': {
    name: 'Weather API',
    status: 'healthy',
    last_check: '2024-12-01T12:00:00Z'
  },
  'carbon-intensity-service': {
    name: 'Carbon Intensity',
    status: 'unhealthy',
    last_check: '2024-12-01T12:01:00Z',
    error_message: 'API key missing'
  }
};

const createFetchMock = (response: ServicesHealthResponse) =>
  vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    statusText: 'OK',
    json: () => Promise.resolve(response)
  } as Response);

describe('AdminApiClient service health utilities', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('fetches the services health endpoint directly', async () => {
    const fetchMock = createFetchMock(mockServicesHealth);
    vi.stubGlobal('fetch', fetchMock);

    const response = await apiService.getServicesHealth();

    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8003/api/v1/health/services', undefined);
    expect(response).toEqual(mockServicesHealth);
  });

  it('maps service health entries into the data sources shape', async () => {
    const fetchMock = createFetchMock(mockServicesHealth);
    vi.stubGlobal('fetch', fetchMock);

    const dataSources = await apiService.getAllDataSources();

    expect(dataSources.weather?.status).toBe('healthy');
    expect(dataSources.weather?.service).toBe('Weather API');
    expect(dataSources.carbonIntensity?.status).toBe('error');
    expect(dataSources.carbonIntensity?.error_message).toBe('API key missing');
    expect(dataSources.airQuality).toBeNull();
  });
});
