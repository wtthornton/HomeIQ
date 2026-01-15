/**
 * Device Picker Component
 * Phase 1: Device-Based Automation Suggestions Feature
 * 
 * Allows users to select a device to get automation suggestions
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { listDevices, getDevice, getDeviceCapabilities, type Device, type DeviceCapabilitiesResponse, DeviceAPIError } from '../../services/deviceApi';
import toast from 'react-hot-toast';

/** Props for DevicePicker component */
interface DevicePickerProps {
  /** Whether dark mode is enabled */
  darkMode: boolean;
  /** Currently selected device ID */
  selectedDeviceId: string | null;
  /** Callback when a device is selected */
  onSelectDevice: (deviceId: string | null) => void;
  /** Whether the picker is open */
  isOpen: boolean;
  /** Callback to toggle picker visibility */
  onToggle: () => void;
}

/**
 * Device Picker Component
 * 
 * Features:
 * - Device search and filtering
 * - Filter by device type, area, manufacturer, model
 * - Display device information
 * - Device selection
 */
export const DevicePicker: React.FC<DevicePickerProps> = ({
  darkMode,
  selectedDeviceId,
  onSelectDevice,
  isOpen,
  onToggle,
}) => {
  const [devices, setDevices] = useState<Device[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [filters, setFilters] = useState({
    device_type: '',
    area_id: '',
    manufacturer: '',
    model: '',
  });
  const [_selectedDevice, setSelectedDevice] = useState<Device | null>(null);
  const [_deviceCapabilities, setDeviceCapabilities] = useState<DeviceCapabilitiesResponse | null>(null);

  // Load devices with filters
  const loadDevices = useCallback(async () => {
    setIsLoading(true);
    try {
      const params: {
        limit?: number;
        device_type?: string;
        area_id?: string;
        manufacturer?: string;
        model?: string;
      } = {
        limit: 100,
      };

      if (filters.device_type) params.device_type = filters.device_type;
      if (filters.area_id) params.area_id = filters.area_id;
      if (filters.manufacturer) params.manufacturer = filters.manufacturer;
      if (filters.model) params.model = filters.model;

      const response = await listDevices(params);
      setDevices(response.devices);
    } catch (error) {
      console.error('Failed to load devices:', error);
      if (error instanceof DeviceAPIError) {
        toast.error(`Failed to load devices: ${error.message}`);
      } else {
        toast.error('Failed to load devices');
      }
    } finally {
      setIsLoading(false);
    }
  }, [filters]);

  // Load selected device details
  const loadDeviceDetails = useCallback(async (deviceId: string) => {
    try {
      const device = await getDevice(deviceId);
      setSelectedDevice(device);

      // Load capabilities
      try {
        const capabilities = await getDeviceCapabilities(deviceId);
        setDeviceCapabilities(capabilities);
      } catch (error) {
        console.warn('Failed to load device capabilities:', error);
        setDeviceCapabilities(null);
      }
    } catch (error) {
      console.error('Failed to load device details:', error);
      if (error instanceof DeviceAPIError) {
        toast.error(`Failed to load device: ${error.message}`);
      } else {
        toast.error('Failed to load device');
      }
    }
  }, []);

  // Load devices when filters change
  useEffect(() => {
    if (isOpen) {
      loadDevices();
    }
  }, [isOpen, loadDevices]);

  // Load selected device details when device is selected
  useEffect(() => {
    if (selectedDeviceId) {
      loadDeviceDetails(selectedDeviceId);
    } else {
      setSelectedDevice(null);
      setDeviceCapabilities(null);
    }
  }, [selectedDeviceId, loadDeviceDetails]);

  // Filter devices by search query
  const filteredDevices = useMemo(() => {
    if (!searchQuery) return devices;
    const query = searchQuery.toLowerCase();
    return devices.filter((device) => {
      const name = device.name.toLowerCase();
      const manufacturer = device.manufacturer.toLowerCase();
      const model = device.model.toLowerCase();
      const area = device.area_id?.toLowerCase() || '';
      return name.includes(query) || 
             manufacturer.includes(query) || 
             model.includes(query) ||
             area.includes(query);
    });
  }, [devices, searchQuery]);

  // Handle device selection
  const handleSelectDevice = (deviceId: string) => {
    onSelectDevice(deviceId);
    onToggle(); // Close picker after selection
    toast.success('Device selected');
  };

  // Handle clear selection
  const handleClearSelection = () => {
    onSelectDevice(null);
    setSelectedDevice(null);
    setDeviceCapabilities(null);
    toast.success('Device selection cleared');
  };

  return (
    <>
      {/* Mobile toggle button - only show when picker is closed */}
      {!isOpen && (
        <button
          onClick={onToggle}
          className={`md:hidden fixed top-20 right-4 z-40 p-2 rounded-lg ${
            darkMode ? 'bg-gray-800 text-white' : 'bg-white text-gray-900'
          } shadow-lg`}
          title="Select Device"
        >
          🔌
        </button>
      )}

      {/* Device Picker Panel */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Overlay for mobile */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={onToggle}
              className="fixed inset-0 bg-black bg-opacity-50 z-30 md:hidden"
            />

            {/* Picker content */}
            <motion.div
              initial={false}
              animate={{ x: 0 }}
              exit={{ x: 300 }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              className={`fixed right-0 top-0 h-full w-96 z-40 flex flex-col ${
                darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
              } border-l shadow-xl md:relative md:z-auto md:shadow-none`}
            >
              {/* Header */}
              <div className={`p-4 border-b ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
                <div className="flex items-center justify-between mb-4">
                  <h2 className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    Select Device
                  </h2>
                  <button
                    onClick={onToggle}
                    className={`md:hidden p-1 rounded ${darkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-100'}`}
                  >
                    ✕
                  </button>
                </div>

                {/* Search */}
                <input
                  type="text"
                  placeholder="Search devices..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className={`w-full px-3 py-2 rounded-lg border ${
                    darkMode
                      ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400'
                      : 'bg-white border-gray-300 text-gray-900 placeholder-gray-500'
                  } focus:outline-none focus:ring-2 focus:ring-blue-500`}
                />

                {/* Filters */}
                <div className="mt-3 space-y-2">
                  <select
                    value={filters.device_type}
                    onChange={(e) => setFilters(prev => ({ ...prev, device_type: e.target.value }))}
                    className={`w-full px-3 py-2 rounded-lg border text-sm ${
                      darkMode
                        ? 'bg-gray-700 border-gray-600 text-white'
                        : 'bg-white border-gray-300 text-gray-900'
                    }`}
                  >
                    <option value="">All Device Types</option>
                    <option value="switch">Switch</option>
                    <option value="light">Light</option>
                    <option value="sensor">Sensor</option>
                    <option value="thermostat">Thermostat</option>
                    <option value="fan">Fan</option>
                    <option value="lock">Lock</option>
                    <option value="camera">Camera</option>
                    <option value="cover">Cover</option>
                    <option value="media_player">Media Player</option>
                    <option value="vacuum">Vacuum</option>
                  </select>

                  <input
                    type="text"
                    placeholder="Filter by area..."
                    value={filters.area_id}
                    onChange={(e) => setFilters(prev => ({ ...prev, area_id: e.target.value }))}
                    className={`w-full px-3 py-2 rounded-lg border text-sm ${
                      darkMode
                        ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400'
                        : 'bg-white border-gray-300 text-gray-900 placeholder-gray-500'
                    }`}
                  />

                  <input
                    type="text"
                    placeholder="Filter by manufacturer..."
                    value={filters.manufacturer}
                    onChange={(e) => setFilters(prev => ({ ...prev, manufacturer: e.target.value }))}
                    className={`w-full px-3 py-2 rounded-lg border text-sm ${
                      darkMode
                        ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400'
                        : 'bg-white border-gray-300 text-gray-900 placeholder-gray-500'
                    }`}
                  />
                </div>

                {/* Clear selection button */}
                {selectedDeviceId && (
                  <button
                    onClick={handleClearSelection}
                    className={`w-full mt-3 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      darkMode
                        ? 'bg-gray-700 text-white hover:bg-gray-600'
                        : 'bg-gray-200 text-gray-900 hover:bg-gray-300'
                    }`}
                  >
                    Clear Selection
                  </button>
                )}
              </div>

              {/* Device List */}
              <div className="flex-1 overflow-y-auto">
                {isLoading ? (
                  <div className="flex items-center justify-center h-32">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
                  </div>
                ) : filteredDevices.length === 0 ? (
                  <div className={`p-4 text-center ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    {filters.device_type ? (
                      <div>
                        <p className="mb-2">No devices found with type "{filters.device_type}"</p>
                        <p className="text-xs opacity-75">
                          Devices may not be classified yet. Try selecting "All Device Types" to see all devices.
                        </p>
                      </div>
                    ) : searchQuery || Object.values(filters).some(f => f) ? (
                      'No devices found matching filters'
                    ) : (
                      'No devices available'
                    )}
                  </div>
                ) : (
                  <div className="p-2" role="listbox" aria-label="Devices">
                    {filteredDevices.map((device) => {
                      const isSelected = device.device_id === selectedDeviceId;
                      
                      return (
                        <motion.div
                          key={device.device_id}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          role="option"
                          aria-selected={isSelected}
                          className={`mb-2 rounded-lg p-3 cursor-pointer transition-colors ${
                            isSelected
                              ? darkMode
                                ? 'bg-blue-600 text-white'
                                : 'bg-blue-500 text-white'
                              : darkMode
                              ? 'bg-gray-700 hover:bg-gray-600 text-gray-200'
                              : 'bg-gray-50 hover:bg-gray-100 text-gray-900'
                          }`}
                          onClick={() => handleSelectDevice(device.device_id)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault();
                              handleSelectDevice(device.device_id);
                            }
                          }}
                          tabIndex={0}
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1 min-w-0">
                              <p className="font-medium truncate">{device.name}</p>
                              <div className="flex items-center gap-2 mt-1 text-xs opacity-75">
                                <span>{device.manufacturer} {device.model}</span>
                                {device.area_id && (
                                  <>
                                    <span aria-hidden="true">•</span>
                                    <span>{device.area_id}</span>
                                  </>
                                )}
                                {device.device_type && (
                                  <>
                                    <span aria-hidden="true">•</span>
                                    <span>{device.device_type}</span>
                                  </>
                                )}
                              </div>
                              {device.entity_count > 0 && (
                                <div className="mt-1 text-xs opacity-75">
                                  {device.entity_count} {device.entity_count === 1 ? 'entity' : 'entities'}
                                </div>
                              )}
                            </div>
                            {isSelected && (
                              <span className="ml-2 text-lg" aria-label="Selected">✓</span>
                            )}
                          </div>
                        </motion.div>
                      );
                    })}
                  </div>
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
};
