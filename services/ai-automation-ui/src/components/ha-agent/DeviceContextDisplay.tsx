/**
 * Device Context Display Component
 * Phase 1: Device-Based Automation Suggestions Feature
 * 
 * Displays selected device information including capabilities and related entities
 */

import React, { useState, useEffect } from 'react';
import { getDevice, getDeviceCapabilities, listEntities, type Device, type DeviceCapabilitiesResponse, type Entity, DeviceAPIError } from '../../services/deviceApi';
import toast from 'react-hot-toast';

/** Props for DeviceContextDisplay component */
interface DeviceContextDisplayProps {
  /** Whether dark mode is enabled */
  darkMode: boolean;
  /** Selected device ID */
  deviceId: string | null;
  /** Callback to clear device selection */
  onClearSelection: () => void;
}

/**
 * Device Context Display Component
 * 
 * Features:
 * - Display device name, manufacturer, model
 * - Show device area/location
 * - Display device capabilities
 * - Show related entities
 * - Device health/status indicators
 */
export const DeviceContextDisplay: React.FC<DeviceContextDisplayProps> = ({
  darkMode,
  deviceId,
  onClearSelection,
}) => {
  const [device, setDevice] = useState<Device | null>(null);
  const [capabilities, setCapabilities] = useState<DeviceCapabilitiesResponse | null>(null);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // Load device details
  useEffect(() => {
    if (!deviceId) {
      setDevice(null);
      setCapabilities(null);
      setEntities([]);
      return;
    }

    const loadDeviceData = async () => {
      setIsLoading(true);
      try {
        // Load device
        const deviceData = await getDevice(deviceId);
        setDevice(deviceData);

        // Load capabilities
        try {
          const capabilitiesData = await getDeviceCapabilities(deviceId);
          setCapabilities(capabilitiesData);
        } catch (error) {
          console.warn('Failed to load device capabilities:', error);
          setCapabilities(null);
        }

        // Load related entities
        try {
          const entitiesResponse = await listEntities({ device_id: deviceId, limit: 50 });
          setEntities(entitiesResponse.entities);
        } catch (error) {
          console.warn('Failed to load device entities:', error);
          setEntities([]);
        }
      } catch (error) {
        console.error('Failed to load device data:', error);
        if (error instanceof DeviceAPIError) {
          toast.error(`Failed to load device: ${error.message}`);
        } else {
          toast.error('Failed to load device');
        }
      } finally {
        setIsLoading(false);
      }
    };

    loadDeviceData();
  }, [deviceId]);

  if (!deviceId || !device) {
    return null;
  }

  if (isLoading) {
    return (
      <div className={`p-4 border-b ${darkMode ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-white'}`}>
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
          <span className={`ml-2 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Loading device...</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`p-4 border-b ${darkMode ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-white'}`}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <h3 className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            {device.name}
          </h3>
          <div className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            <span>{device.manufacturer} {device.model}</span>
            {device.area_id && (
              <>
                <span className="mx-2">•</span>
                <span>{device.area_id}</span>
              </>
            )}
          </div>
        </div>
        <button
          onClick={onClearSelection}
          className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
            darkMode
              ? 'bg-gray-700 text-white hover:bg-gray-600'
              : 'bg-gray-200 text-gray-900 hover:bg-gray-300'
          }`}
        >
          Clear
        </button>
      </div>

      {/* Device Status */}
      <div className="flex items-center gap-2 mb-3">
        <span
          className={`px-2 py-1 rounded text-xs font-medium ${
            device.status === 'active'
              ? darkMode
                ? 'bg-green-500/20 text-green-400'
                : 'bg-green-100 text-green-700'
              : darkMode
              ? 'bg-gray-600 text-gray-400'
              : 'bg-gray-200 text-gray-600'
          }`}
        >
          {device.status === 'active' ? '🟢 Active' : '⚫ Inactive'}
        </span>
        {device.device_type && (
          <span
            className={`px-2 py-1 rounded text-xs font-medium ${
              darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-700'
            }`}
          >
            {device.device_type}
          </span>
        )}
        {device.entity_count > 0 && (
          <span
            className={`px-2 py-1 rounded text-xs font-medium ${
              darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-700'
            }`}
          >
            {device.entity_count} {device.entity_count === 1 ? 'entity' : 'entities'}
          </span>
        )}
      </div>

      {/* Device Capabilities */}
      {capabilities && capabilities.capabilities.length > 0 && (
        <div className="mb-3">
          <h4 className={`text-sm font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
            Capabilities:
          </h4>
          <div className="flex flex-wrap gap-2">
            {capabilities.capabilities.map((cap, idx) => (
              <span
                key={idx}
                className={`px-2 py-1 rounded text-xs ${
                  darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-700'
                }`}
              >
                {cap.capability_name}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Related Entities */}
      {entities.length > 0 && (
        <div>
          <h4 className={`text-sm font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
            Related Entities:
          </h4>
          <div className="flex flex-wrap gap-2">
            {entities.slice(0, 5).map((entity) => (
              <span
                key={entity.entity_id}
                className={`px-2 py-1 rounded text-xs ${
                  darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-700'
                }`}
                title={entity.friendly_name || entity.entity_id}
              >
                {entity.friendly_name || entity.name || entity.entity_id}
              </span>
            ))}
            {entities.length > 5 && (
              <span
                className={`px-2 py-1 rounded text-xs ${
                  darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-700'
                }`}
              >
                +{entities.length - 5} more
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
