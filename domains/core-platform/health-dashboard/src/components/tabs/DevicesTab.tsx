import React, { useState, useMemo, useEffect } from 'react';
import { useDevices, Device, Entity } from '../../hooks/useDevices';
import { dataApi } from '../../services/api';
import type { TabProps } from './types';

export const DevicesTab: React.FC<TabProps> = ({ darkMode }) => {
  const { devices, entities, loading, error, refresh } = useDevices();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedManufacturer, setSelectedManufacturer] = useState('');
  const [selectedArea, setSelectedArea] = useState('');
  const [selectedPlatform, setSelectedPlatform] = useState('');
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);
  const [deviceEntities, setDeviceEntities] = useState<Entity[]>([]);
  const [loadingEntities, setLoadingEntities] = useState(false);
  const [expandedEntity, setExpandedEntity] = useState<string | null>(null);

  // Check for integration context from URL (Phase 1.3)
  React.useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const integrationParam = urlParams.get('integration');
    if (integrationParam) {
      setSelectedPlatform(integrationParam);
      // Clear URL param after setting filter
      urlParams.delete('integration');
      const newUrl = `${window.location.pathname}${urlParams.toString() ? `?${  urlParams.toString()}` : ''}`;
      window.history.replaceState({}, '', newUrl);
    }
  }, []);

  // Get unique manufacturers, areas, and platforms for filters
  const manufacturers = useMemo(() => {
    const unique = Array.from(new Set(devices.map(d => d.manufacturer).filter(Boolean)));
    return unique.sort();
  }, [devices]);

  const areas = useMemo(() => {
    const unique = Array.from(new Set(devices.map(d => d.area_id).filter(Boolean)));
    return unique.sort();
  }, [devices]);

  const platforms = useMemo(() => {
    const unique = Array.from(new Set(entities.map(e => e.platform).filter(Boolean)));
    return unique.sort();
  }, [entities]);

  // Filter devices (enhanced with platform filtering)
  const filteredDevices = useMemo(() => {
    return devices.filter(device => {
      const matchesSearch = !searchTerm || 
        device.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        device.manufacturer?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        device.model?.toLowerCase().includes(searchTerm.toLowerCase());
      
      const matchesManufacturer = !selectedManufacturer || 
        device.manufacturer === selectedManufacturer;
      
      const matchesArea = !selectedArea || 
        device.area_id === selectedArea;
      
      // Platform filtering: check if device has any entity with the selected platform
      const matchesPlatform = !selectedPlatform || 
        entities.some(e => e.device_id === device.device_id && e.platform === selectedPlatform);
      
      return matchesSearch && matchesManufacturer && matchesArea && matchesPlatform;
    });
  }, [devices, entities, searchTerm, selectedManufacturer, selectedArea, selectedPlatform]);

  // Get device icon
  const getDeviceIcon = (device: Device): string => {
    const name = device.name.toLowerCase();
    const manufacturer = device.manufacturer?.toLowerCase() || '';
    const model = device.model?.toLowerCase() || '';
    
    if (name.includes('light') || name.includes('bulb') || name.includes('lamp') || manufacturer.includes('hue') || manufacturer.includes('lifx')) return '💡';
    if (name.includes('thermostat') || name.includes('climate') || manufacturer.includes('nest') || manufacturer.includes('ecobee')) return '🌡️';
    if (name.includes('camera') || name.includes('cam') || manufacturer.includes('ring') || manufacturer.includes('arlo')) return '📷';
    if (name.includes('switch') || name.includes('outlet') || name.includes('plug')) return '🔌';
    if (name.includes('lock') || name.includes('door lock')) return '🔒';
    if (name.includes('cover') || name.includes('blind') || name.includes('shade') || name.includes('garage')) return '🚪';
    if (name.includes('sensor')) return '📱';
    if (name.includes('media') || name.includes('sonos') || name.includes('chromecast')) return '🎵';
    if (name.includes('vacuum') || name.includes('roomba')) return '🤖';
    if (name.includes('hub') || name.includes('bridge') || model.includes('bridge')) return '🔧';
    
    return '📦'; // Default
  };

  // Fetch entities for selected device directly from API
  // Context7 Best Practice: Only depend on selectedDevice, not global entities array
  useEffect(() => {
    if (selectedDevice) {
      console.log(`[DeviceEntities] Fetching entities for device: ${selectedDevice.device_id} (entity_count: ${selectedDevice.entity_count})`);
      setLoadingEntities(true);
      
      // If device shows entity_count > 0 but API returns none, we have a data mismatch issue
      const expectedEntityCount = selectedDevice.entity_count || 0;
      
      dataApi.getEntities({ device_id: selectedDevice.device_id, limit: 100 })
        .then(response => {
          console.log('[DeviceEntities] API response:', response);
          const apiEntities = response?.entities || [];
          console.log(`[DeviceEntities] Received ${apiEntities.length} entities (expected ${expectedEntityCount})`);
          
          if (expectedEntityCount > 0 && apiEntities.length === 0) {
            console.warn(`[DeviceEntities] ⚠️ Data mismatch: Device shows ${expectedEntityCount} entities but API returned none.`);
          }
          
          setDeviceEntities(apiEntities);
        })
        .catch(err => {
          console.error('[DeviceEntities] Error fetching entities:', err);
          setDeviceEntities([]);
        })
        .finally(() => {
          setLoadingEntities(false);
        });
    } else {
      setDeviceEntities([]);
    }
  }, [selectedDevice]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className={`text-3xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            Devices
          </h1>
          <p className={`mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            Manage and monitor your Home Assistant devices
          </p>
        </div>
        <button
          onClick={refresh}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            darkMode
              ? 'bg-blue-600 hover:bg-blue-700 text-white'
              : 'bg-blue-500 hover:bg-blue-600 text-white'
          }`}
        >
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className={`p-4 rounded-lg ${darkMode ? 'bg-gray-800' : 'bg-gray-50'}`}>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Search */}
          <div>
            <label className={`block text-sm font-medium mb-1 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              Search
            </label>
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search devices..."
              className={`w-full px-3 py-2 rounded border ${
                darkMode
                  ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400'
                  : 'bg-white border-gray-300 text-gray-900 placeholder-gray-500'
              }`}
            />
          </div>

          {/* Manufacturer Filter */}
          <div>
            <label className={`block text-sm font-medium mb-1 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              Manufacturer
            </label>
            <select
              value={selectedManufacturer}
              onChange={(e) => setSelectedManufacturer(e.target.value)}
              className={`w-full px-3 py-2 rounded border ${
                darkMode
                  ? 'bg-gray-700 border-gray-600 text-white'
                  : 'bg-white border-gray-300 text-gray-900'
              }`}
            >
              <option value="">All Manufacturers</option>
              {manufacturers.map(manufacturer => (
                <option key={manufacturer} value={manufacturer}>{manufacturer}</option>
              ))}
            </select>
          </div>

          {/* Area Filter */}
          <div>
            <label className={`block text-sm font-medium mb-1 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              Area
            </label>
            <select
              value={selectedArea}
              onChange={(e) => setSelectedArea(e.target.value)}
              className={`w-full px-3 py-2 rounded border ${
                darkMode
                  ? 'bg-gray-700 border-gray-600 text-white'
                  : 'bg-white border-gray-300 text-gray-900'
              }`}
            >
              <option value="">All Areas</option>
              {areas.map(area => (
                <option key={area} value={area}>{area}</option>
              ))}
            </select>
          </div>

          {/* Platform Filter */}
          <div>
            <label className={`block text-sm font-medium mb-1 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              Platform
            </label>
            <select
              value={selectedPlatform}
              onChange={(e) => setSelectedPlatform(e.target.value)}
              className={`w-full px-3 py-2 rounded border ${
                darkMode
                  ? 'bg-gray-700 border-gray-600 text-white'
                  : 'bg-white border-gray-300 text-gray-900'
              }`}
            >
              <option value="">All Platforms</option>
              {platforms.map(platform => (
                <option key={platform} value={platform}>{platform}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className={`text-center py-12 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-4">Loading devices...</p>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className={`p-4 rounded-lg border ${darkMode ? 'bg-red-900/20 border-red-700 text-red-400' : 'bg-red-50 border-red-200 text-red-800'}`}>
          <p className="font-medium">Error loading devices</p>
          <p className="text-sm mt-1">{error}</p>
        </div>
      )}

      {/* Devices Grid */}
      {!loading && !error && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filteredDevices.map(device => (
            <button
              key={device.device_id}
              onClick={() => setSelectedDevice(device)}
              className={`p-4 rounded-lg border text-left transition-all duration-200 ${
                darkMode 
                  ? 'bg-gray-800 border-gray-700 hover:bg-gray-750 hover:border-blue-600' 
                  : 'bg-white border-gray-200 hover:bg-gray-50 hover:border-blue-400'
              } hover:shadow-lg hover:scale-105`}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="text-4xl">{getDeviceIcon(device)}</div>
                <div className="flex flex-col items-end gap-1">
                  <div className={`text-xs px-2 py-1 rounded ${
                    darkMode ? 'bg-gray-700' : 'bg-gray-100'
                  }`}>
                    {device.entity_count} {device.entity_count === 1 ? 'entity' : 'entities'}
                  </div>
                  {/* Device Status Badge */}
                  {device.status && (
                    <div className={`text-xs px-2 py-1 rounded font-medium ${
                      device.status === 'active'
                        ? darkMode 
                          ? 'bg-green-900/50 text-green-300 border border-green-700/50' 
                          : 'bg-green-100 text-green-700 border border-green-300'
                        : darkMode
                          ? 'bg-gray-700/50 text-gray-400 border border-gray-600/50'
                          : 'bg-gray-200 text-gray-600 border border-gray-300'
                    }`}>
                      {device.status === 'active' ? '● Active' : '○ Inactive'}
                    </div>
                  )}
                </div>
              </div>

              <h3 className={`font-semibold mb-1 ${darkMode ? 'text-gray-100' : 'text-gray-900'}`}>
                {device.name}
              </h3>

              <div className={`text-xs space-y-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                <div>🏭 {device.manufacturer || 'Unknown'}</div>
                <div>📦 {device.model || 'Unknown'}</div>
                {device.model_id && device.model_id !== device.model && (
                  <div className="text-xs opacity-70">🆔 Model ID: {device.model_id}</div>
                )}
                {device.sw_version && <div>💾 {device.sw_version}</div>}
                {device.serial_number && <div>🔢 Serial: {device.serial_number}</div>}
                {device.area_id && <div>📍 {device.area_id}</div>}
                {device.timestamp && (
                  <div className="text-xs opacity-70">⏰ {formatTimeAgo(device.timestamp)}</div>
                )}
                {/* Priority 1.3: Device Integration */}
                {device.integration && (
                  <div className={`text-xs px-2 py-0.5 rounded inline-block mt-1 ${
                    darkMode ? 'bg-blue-900/30 text-blue-300' : 'bg-blue-100 text-blue-700'
                  }`}>
                    🔌 {device.integration}
                  </div>
                )}
                {device.config_entry_id && (
                  <div className="text-xs opacity-70">⚙️ Config: {device.config_entry_id.substring(0, 8)}...</div>
                )}
                {device.via_device && (
                  <div className="text-xs opacity-70">🔗 Via: {device.via_device}</div>
                )}
                {/* Priority 2.1: Device Type & Category */}
                {(device.device_type || device.device_category) && (
                  <div className="flex flex-wrap gap-1 mt-1">
                    {device.device_type && (
                      <span className={`text-xs px-2 py-0.5 rounded ${
                        darkMode ? 'bg-purple-900/30 text-purple-300' : 'bg-purple-100 text-purple-700'
                      }`}>
                        {device.device_type}
                      </span>
                    )}
                    {device.device_category && (
                      <span className={`text-xs px-2 py-0.5 rounded ${
                        darkMode ? 'bg-indigo-900/30 text-indigo-300' : 'bg-indigo-100 text-indigo-700'
                      }`}>
                        {device.device_category}
                      </span>
                    )}
                  </div>
                )}
                {/* Power Consumption (if available) */}
                {(device.power_consumption_idle_w || device.power_consumption_active_w || device.power_consumption_max_w) && (
                  <div className="flex flex-wrap gap-1 mt-1 text-xs opacity-70">
                    ⚡
                    {device.power_consumption_idle_w && <span>Idle: {device.power_consumption_idle_w}W</span>}
                    {device.power_consumption_active_w && <span>Active: {device.power_consumption_active_w}W</span>}
                    {device.power_consumption_max_w && <span>Max: {device.power_consumption_max_w}W</span>}
                  </div>
                )}
                {/* Community Rating (if available) */}
                {device.community_rating && (
                  <div className="text-xs opacity-70">⭐ Rating: {device.community_rating}/10</div>
                )}
                {/* Priority 2.3: Device Labels */}
                {device.labels && device.labels.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1">
                    {device.labels.map((label, idx) => (
                      <span key={idx} className={`text-xs px-2 py-0.5 rounded ${
                        darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-700'
                      }`}>
                        {label}
                      </span>
                    ))}
                  </div>
                )}
                {/* Entities Section - Show all entities with capabilities and services */}
                {(() => {
                  const deviceEntitiesList = entities.filter(e => e.device_id === device.device_id);
                  if (deviceEntitiesList.length > 0) {
                    return (
                      <div className="mt-3 pt-2 border-t border-gray-600 dark:border-gray-600">
                        <div className={`text-xs font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                          🔌 Entities ({deviceEntitiesList.length})
                        </div>
                        <div className="space-y-2 max-h-48 overflow-y-auto">
                          {deviceEntitiesList.slice(0, 5).map((entity: Entity) => (
                            <div
                              key={entity.entity_id}
                              className={`p-2 rounded text-xs ${
                                darkMode ? 'bg-gray-750 border border-gray-600' : 'bg-gray-50 border border-gray-200'
                              }`}
                            >
                              {/* Entity Name */}
                              <div className="flex items-center gap-1 mb-1">
                                <span>{getDomainIcon(entity.domain)}</span>
                                <span className="font-medium">
                                  {entity.friendly_name || entity.name || entity.entity_id.split('.')[1]}
                                </span>
                                <span className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
                                  ({entity.domain})
                                </span>
                              </div>
                              {/* Entity Capabilities */}
                              {entity.capabilities && entity.capabilities.length > 0 && (
                                <div className="mt-1 flex flex-wrap gap-1">
                                  {entity.capabilities.slice(0, 3).map((cap, idx) => (
                                    <span key={idx} className={`text-xs px-1.5 py-0.5 rounded ${
                                      darkMode ? 'bg-blue-900/30 text-blue-300' : 'bg-blue-100 text-blue-700'
                                    }`}>
                                      {cap}
                                    </span>
                                  ))}
                                  {entity.capabilities.length > 3 && (
                                    <span className={`text-xs px-1.5 py-0.5 rounded ${
                                      darkMode ? 'bg-gray-700 text-gray-400' : 'bg-gray-200 text-gray-600'
                                    }`}>
                                      +{entity.capabilities.length - 3}
                                    </span>
                                  )}
                                </div>
                              )}
                              {/* Available Services (Actions) */}
                              {entity.available_services && entity.available_services.length > 0 && (
                                <div className="mt-1">
                                  <div className={`text-xs font-medium ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                                    Actions:
                                  </div>
                                  <div className="flex flex-wrap gap-1 mt-0.5">
                                    {entity.available_services.slice(0, 2).map((service, idx) => (
                                      <span key={idx} className={`text-xs px-1.5 py-0.5 rounded font-mono ${
                                        darkMode ? 'bg-green-900/30 text-green-300' : 'bg-green-100 text-green-700'
                                      }`}>
                                        {service.split('.')[1]}
                                      </span>
                                    ))}
                                    {entity.available_services.length > 2 && (
                                      <span className={`text-xs px-1.5 py-0.5 rounded ${
                                        darkMode ? 'bg-gray-700 text-gray-400' : 'bg-gray-200 text-gray-600'
                                      }`}>
                                        +{entity.available_services.length - 2}
                                      </span>
                                    )}
                                  </div>
                                </div>
                              )}
                            </div>
                          ))}
                          {deviceEntitiesList.length > 5 && (
                            <div className={`text-xs text-center italic ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
                              ... and {deviceEntitiesList.length - 5} more (click to view all)
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  }
                  return null;
                })()}
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Entity Browser Modal */}
      {selectedDevice && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
          onClick={() => {
            setSelectedDevice(null);
            setExpandedEntity(null);
          }}
        >
          <div 
            className={`max-w-4xl w-full max-h-[90vh] overflow-auto rounded-lg ${
              darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
            } border shadow-2xl`}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className={`sticky top-0 p-6 border-b ${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-4xl">{getDeviceIcon(selectedDevice)}</span>
                    <h2 className="text-2xl font-bold">{selectedDevice.name}</h2>
                  </div>
                  <div className={`text-sm space-y-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    <div>🏭 {selectedDevice.manufacturer}</div>
                    <div>📦 {selectedDevice.model}</div>
                    {selectedDevice.model_id && selectedDevice.model_id !== selectedDevice.model && (
                      <div>🆔 Model ID: <span className="font-medium">{selectedDevice.model_id}</span></div>
                    )}
                    {selectedDevice.sw_version && <div>💾 {selectedDevice.sw_version}</div>}
                    {selectedDevice.serial_number && (
                      <div>🔢 Serial Number: <span className="font-medium">{selectedDevice.serial_number}</span></div>
                    )}
                    {selectedDevice.area_id && <div>📍 {selectedDevice.area_id}</div>}
                    {/* Priority 1.3: Device Integration */}
                    {selectedDevice.integration && (
                      <div>🔌 Integration: <span className="font-medium">{selectedDevice.integration}</span></div>
                    )}
                    {selectedDevice.config_entry_id && (
                      <div>⚙️ Config Entry: <span className="font-mono text-xs">{selectedDevice.config_entry_id.substring(0, 16)}...</span></div>
                    )}
                    {/* Priority 1.5: Last Seen Timestamp */}
                    {selectedDevice.timestamp && (
                      <div>⏰ Last seen: <span className="font-medium">{formatTimeAgo(selectedDevice.timestamp)}</span></div>
                    )}
                    {/* Priority 2.1: Device Type & Category */}
                    {(selectedDevice.device_type || selectedDevice.device_category) && (
                      <div className="flex flex-wrap gap-2 mt-2">
                        {selectedDevice.device_type && (
                          <span className={`text-xs px-2 py-1 rounded ${
                            darkMode ? 'bg-purple-900/30 text-purple-300' : 'bg-purple-100 text-purple-700'
                          }`}>
                            Type: {selectedDevice.device_type}
                          </span>
                        )}
                        {selectedDevice.device_category && (
                          <span className={`text-xs px-2 py-1 rounded ${
                            darkMode ? 'bg-indigo-900/30 text-indigo-300' : 'bg-indigo-100 text-indigo-700'
                          }`}>
                            Category: {selectedDevice.device_category}
                          </span>
                        )}
                      </div>
                    )}
                    {/* Power Consumption (if available) */}
                    {(selectedDevice.power_consumption_idle_w || selectedDevice.power_consumption_active_w || selectedDevice.power_consumption_max_w) && (
                      <div className="mt-2 space-y-1">
                        <div className="font-medium">⚡ Power Consumption:</div>
                        {selectedDevice.power_consumption_idle_w && (
                          <div className="ml-4 text-xs">Idle: {selectedDevice.power_consumption_idle_w}W</div>
                        )}
                        {selectedDevice.power_consumption_active_w && (
                          <div className="ml-4 text-xs">Active: {selectedDevice.power_consumption_active_w}W</div>
                        )}
                        {selectedDevice.power_consumption_max_w && (
                          <div className="ml-4 text-xs">Max: {selectedDevice.power_consumption_max_w}W</div>
                        )}
                      </div>
                    )}
                    {/* Community Rating (if available) */}
                    {selectedDevice.community_rating && (
                      <div>⭐ Community Rating: <span className="font-medium">{selectedDevice.community_rating}/10</span></div>
                    )}
                    {/* Setup Instructions (if available) */}
                    {selectedDevice.setup_instructions_url && (
                      <div>📖 Setup Guide: <a href={selectedDevice.setup_instructions_url} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">View Instructions</a></div>
                    )}
                    {/* Last Capability Sync (if available) */}
                    {selectedDevice.last_capability_sync && (
                      <div>
                        🔄 Capabilities synced:{' '}
                        <span className="font-medium">
                          {formatTimeAgo(selectedDevice.last_capability_sync)}
                        </span>
                      </div>
                    )}
                    {/* Priority 2.4: Via Device (Parent Device) */}
                    {selectedDevice.via_device && (
                      <div className="mt-2">
                        🔗 Connected via: <span className="font-medium">{selectedDevice.via_device}</span>
                      </div>
                    )}
                    {/* Priority 2.3: Device Labels */}
                    {selectedDevice.labels && selectedDevice.labels.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {selectedDevice.labels.map((label, idx) => (
                          <span key={idx} className={`text-xs px-2 py-1 rounded ${
                            darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-700'
                          }`}>
                            {label}
                          </span>
                        ))}
                      </div>
                    )}
                    {/* Troubleshooting Notes (if available) */}
                    {selectedDevice.troubleshooting_notes && (
                      <div className="mt-3 p-2 rounded bg-yellow-900/20 border border-yellow-700/50 text-xs">
                        <div className="font-medium mb-1">⚠️ Troubleshooting:</div>
                        <div>{selectedDevice.troubleshooting_notes}</div>
                      </div>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => {
                    setSelectedDevice(null);
                    setExpandedEntity(null);
                  }}
                  className={`text-2xl ${darkMode ? 'text-gray-400 hover:text-gray-200' : 'text-gray-600 hover:text-gray-900'}`}
                >
                  ×
                </button>
              </div>
            </div>

            {/* Entities */}
            <div className="p-6">
              <h3 className={`text-lg font-semibold mb-4 ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
                Entities ({loadingEntities ? '...' : deviceEntities.length})
              </h3>

              {loadingEntities ? (
                <div className={`text-center py-8 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
                  <p className="mt-2">Loading entities...</p>
                </div>
              ) : deviceEntities.length === 0 ? (
                <div className={`text-center py-8 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                  <div className="text-4xl mb-2">🔌</div>
                  <p>No entities found for this device</p>
                  {selectedDevice.entity_count && selectedDevice.entity_count > 0 && (
                    <p className="text-sm mt-2 text-yellow-600 dark:text-yellow-400">
                      ⚠️ Device shows {selectedDevice.entity_count} entities, but none were returned by the API.
                      <br />
                      This may indicate a data sync issue. Check the browser console for details.
                    </p>
                  )}
                </div>
              ) : (
                <div className="space-y-2">
                  {Object.entries(groupByDomain(deviceEntities)).map(([domain, domainEntities]) => (
                    <div key={domain}>
                      <div className={`text-sm font-medium mb-2 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                        {getDomainIcon(domain)} {domain} ({domainEntities.length})
                      </div>
                      <div className="space-y-1 ml-6">
                        {domainEntities.map((entity: Entity) => (
                          <div
                            key={entity.entity_id}
                            className={`p-3 rounded ${darkMode ? 'bg-gray-750 border-gray-600' : 'bg-gray-50 border-gray-200'} border`}
                          >
                            <div className="flex items-start justify-between gap-2">
                              <div className="flex-1">
                                {/* Priority 1.1: Entity Friendly Name (Primary) */}
                                <div className="flex items-center gap-2">
                                  {/* Priority 1.2: Entity Icon */}
                                  <span className="text-lg">{getEntityIcon(entity)}</span>
                                  <div className="font-medium">
                                    {entity.friendly_name || entity.name || entity.entity_id}
                                  </div>
                                </div>
                                {/* Entity ID (Secondary - smaller text) */}
                                <code className={`text-xs font-mono block mt-1 ${
                                  entity.disabled 
                                    ? (darkMode ? 'text-gray-600' : 'text-gray-400')
                                    : (darkMode ? 'text-gray-500' : 'text-gray-500')
                                }`}>
                                  {entity.entity_id}
                                </code>
                                {/* Platform */}
                                <div className={`text-xs mt-1 ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
                                  Platform: {entity.platform}
                                </div>
                                {/* Priority 1.4: Device Class & Unit */}
                                {(entity.device_class || entity.unit_of_measurement) && (
                                  <div className="flex flex-wrap gap-2 mt-2">
                                    {entity.device_class && (
                                      <span className={`text-xs px-2 py-0.5 rounded ${
                                        darkMode ? 'bg-blue-900/30 text-blue-300' : 'bg-blue-100 text-blue-700'
                                      }`}>
                                        {entity.device_class}
                                      </span>
                                    )}
                                    {entity.unit_of_measurement && (
                                      <span className={`text-xs px-2 py-0.5 rounded ${
                                        darkMode ? 'bg-green-900/30 text-green-300' : 'bg-green-100 text-green-700'
                                      }`}>
                                        {entity.unit_of_measurement}
                                      </span>
                                    )}
                                  </div>
                                )}
                                {/* Priority 2.2: Entity Capabilities (Expandable) */}
                                {entity.capabilities && entity.capabilities.length > 0 && (
                                  <div className="mt-2">
                                    <button
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        setExpandedEntity(expandedEntity === entity.entity_id ? null : entity.entity_id);
                                      }}
                                      className={`text-xs font-medium ${darkMode ? 'text-blue-400 hover:text-blue-300' : 'text-blue-600 hover:text-blue-700'}`}
                                    >
                                      {expandedEntity === entity.entity_id ? '▼' : '▶'} Capabilities ({entity.capabilities.length})
                                    </button>
                                    {expandedEntity === entity.entity_id && (
                                      <div className="mt-1 ml-4 space-y-2">
                                        <div className="flex flex-wrap gap-1">
                                          {entity.capabilities.map((capability, idx) => (
                                            <span key={idx} className={`text-xs px-2 py-0.5 rounded ${
                                              darkMode ? 'bg-blue-900/30 text-blue-300' : 'bg-blue-100 text-blue-700'
                                            }`}>
                                              {capability}
                                            </span>
                                          ))}
                                        </div>
                                        {/* Available Services (Actions for AI/Automation) */}
                                        {entity.available_services && entity.available_services.length > 0 && (
                                          <div className="mt-2 pt-2 border-t border-gray-600 dark:border-gray-600">
                                            <div className={`text-xs font-medium mb-1 ${darkMode ? 'text-green-400' : 'text-green-700'}`}>
                                              🤖 Available Actions ({entity.available_services.length}):
                                            </div>
                                            <div className="flex flex-wrap gap-1">
                                              {entity.available_services.map((service, idx) => (
                                                <span key={idx} className={`text-xs px-2 py-0.5 rounded font-mono ${
                                                  darkMode ? 'bg-green-900/30 text-green-300' : 'bg-green-100 text-green-700'
                                                }`}>
                                                  {service}
                                                </span>
                                              ))}
                                            </div>
                                          </div>
                                        )}
                                        {/* Entity Options/Settings */}
                                        {entity.options && Object.keys(entity.options).length > 0 && (
                                          <div className="mt-2 pt-2 border-t border-gray-600 dark:border-gray-600">
                                            <div className={`text-xs font-medium mb-1 ${darkMode ? 'text-yellow-400' : 'text-yellow-700'}`}>
                                              ⚙️ Configurable Settings:
                                            </div>
                                            <div className="space-y-1">
                                              {Object.entries(entity.options).map(([key, value]) => (
                                                <div key={key} className={`text-xs px-2 py-0.5 rounded ${
                                                  darkMode ? 'bg-yellow-900/20 text-yellow-300' : 'bg-yellow-50 text-yellow-800'
                                                }`}>
                                                  <span className="font-medium">{key}:</span> {String(value)}
                                                </div>
                                              ))}
                                            </div>
                                          </div>
                                        )}
                                        {/* Aliases (for entity resolution) */}
                                        {entity.aliases && entity.aliases.length > 0 && (
                                          <div className="mt-2 pt-2 border-t border-gray-600 dark:border-gray-600">
                                            <div className={`text-xs font-medium mb-1 ${darkMode ? 'text-purple-400' : 'text-purple-700'}`}>
                                              🏷️ Aliases ({entity.aliases.length}):
                                            </div>
                                            <div className="flex flex-wrap gap-1">
                                              {entity.aliases.map((alias, idx) => (
                                                <span key={idx} className={`text-xs px-2 py-0.5 rounded ${
                                                  darkMode ? 'bg-purple-900/30 text-purple-300' : 'bg-purple-100 text-purple-700'
                                                }`}>
                                                  {alias}
                                                </span>
                                              ))}
                                            </div>
                                          </div>
                                        )}
                                        {/* Supported Features (bitmask) */}
                                        {entity.supported_features !== undefined && entity.supported_features !== null && (
                                          <div className="mt-2 pt-2 border-t border-gray-600 dark:border-gray-600">
                                            <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                                              🔧 Supported Features: <span className="font-mono">{entity.supported_features}</span>
                                            </div>
                                          </div>
                                        )}
                                      </div>
                                    )}
                                  </div>
                                )}
                                {/* Show available services even when not expanded (if no capabilities) */}
                                {(!entity.capabilities || entity.capabilities.length === 0) && entity.available_services && entity.available_services.length > 0 && (
                                  <div className="mt-2">
                                    <div className={`text-xs font-medium mb-1 ${darkMode ? 'text-green-400' : 'text-green-700'}`}>
                                      🤖 Actions ({entity.available_services.length}):
                                    </div>
                                    <div className="flex flex-wrap gap-1">
                                      {entity.available_services.slice(0, 3).map((service, idx) => (
                                        <span key={idx} className={`text-xs px-2 py-0.5 rounded font-mono ${
                                          darkMode ? 'bg-green-900/30 text-green-300' : 'bg-green-100 text-green-700'
                                        }`}>
                                          {service.split('.')[1]}
                                        </span>
                                      ))}
                                      {entity.available_services.length > 3 && (
                                        <button
                                          onClick={(e) => {
                                            e.stopPropagation();
                                            setExpandedEntity(expandedEntity === entity.entity_id ? null : entity.entity_id);
                                          }}
                                          className={`text-xs px-2 py-0.5 rounded ${
                                            darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-700'
                                          }`}
                                        >
                                          +{entity.available_services.length - 3} more
                                        </button>
                                      )}
                                    </div>
                                  </div>
                                )}
                                {/* Priority 2.3: Entity Labels */}
                                {entity.labels && entity.labels.length > 0 && (
                                  <div className="flex flex-wrap gap-1 mt-2">
                                    {entity.labels.map((label, idx) => (
                                      <span key={idx} className={`text-xs px-2 py-0.5 rounded ${
                                        darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-700'
                                      }`}>
                                        {label}
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </div>
                              {entity.disabled && (
                                <span className={`text-xs px-2 py-1 rounded ${
                                  darkMode ? 'bg-gray-700 text-gray-400' : 'bg-gray-200 text-gray-600'
                                }`}>
                                  Disabled
                                </span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Helper functions
function groupByDomain(entities: Entity[]): Record<string, Entity[]> {
  return entities.reduce((acc, entity) => {
    const domain = entity.domain || 'unknown';
    if (!acc[domain]) acc[domain] = [];
    acc[domain].push(entity);
    return acc;
  }, {} as Record<string, Entity[]>);
}

function getDomainIcon(domain: string): string {
  const icons: Record<string, string> = {
    light: '💡',
    sensor: '📊',
    switch: '🔌',
    climate: '🌡️',
    camera: '📷',
    lock: '🔒',
    cover: '🚪',
    binary_sensor: '🔘',
    media_player: '🎵',
    vacuum: '🤖',
    fan: '🌀',
    automation: '⚙️',
    script: '📝',
    scene: '🎭',
    person: '👤',
    device_tracker: '📍',
    sun: '☀️',
    weather: '🌤️',
  };
  
  return icons[domain] || '🔌';
}

// Priority 1.2: Get Entity Icon (use entity.icon if available, fallback to domain icon)
function getEntityIcon(entity: Entity): string {
  // If entity has an icon, use it (Home Assistant uses mdi: format, but we use emojis as fallback)
  // For now, fallback to domain icon since we're using emojis
  // Future: Could map mdi: icons to emojis or use an icon library
  return getDomainIcon(entity.domain);
}

// Priority 1.5: Format relative time (e.g., "2 hours ago")
function formatTimeAgo(timestamp: string | undefined): string {
  if (!timestamp) return 'N/A';
  try {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);
    
    if (diffSecs < 60) return `${diffSecs}s ago`;
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 30) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  } catch {
    return 'N/A';
  }
}