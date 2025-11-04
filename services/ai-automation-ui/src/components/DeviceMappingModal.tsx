/**
 * Device Mapping Modal Component
 * 
 * Allows users to change which entity_id maps to a friendly_name in an automation suggestion.
 * Shows current mapping, searchable list of alternative entities, and device capabilities.
 */

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import api from '../services/api';

interface EntityOption {
  entity_id: string;
  friendly_name: string;
  domain: string;
  state?: string;
  capabilities?: string[];
  device_id?: string;
  area_id?: string;
}

interface DeviceMappingModalProps {
  isOpen: boolean;
  friendlyName: string;
  currentEntityId: string;
  currentDomain?: string;
  onSave: (friendlyName: string, newEntityId: string) => void;
  onCancel: () => void;
  darkMode?: boolean;
}

export const DeviceMappingModal: React.FC<DeviceMappingModalProps> = ({
  isOpen,
  friendlyName,
  currentEntityId,
  currentDomain,
  onSave,
  onCancel,
  darkMode = false
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [entities, setEntities] = useState<EntityOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedEntityId, setSelectedEntityId] = useState<string>(currentEntityId);
  const [error, setError] = useState<string | null>(null);

  // Fetch entities when modal opens or search term changes
  useEffect(() => {
    if (!isOpen) return;

    const fetchEntities = async () => {
      setLoading(true);
      setError(null);
      try {
        const results = await api.searchEntities({
          domain: currentDomain || undefined,
          search_term: searchTerm || undefined,
          limit: 50
        });
        setEntities(results);
      } catch (err) {
        console.error('Failed to search entities:', err);
        setError('Failed to load entities. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    // Debounce search
    const timer = setTimeout(fetchEntities, 300);
    return () => clearTimeout(timer);
  }, [isOpen, searchTerm, currentDomain]);

  // Reset selected entity when modal opens
  useEffect(() => {
    if (isOpen) {
      setSelectedEntityId(currentEntityId);
      setSearchTerm('');
    }
  }, [isOpen, currentEntityId]);

  const handleSave = () => {
    if (selectedEntityId && selectedEntityId !== currentEntityId) {
      onSave(friendlyName, selectedEntityId);
    } else {
      onCancel();
    }
  };

  const handleEntitySelect = (entityId: string) => {
    setSelectedEntityId(entityId);
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center"
        style={{ background: 'rgba(0, 0, 0, 0.7)' }}
        onClick={onCancel}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          className={`w-full max-w-2xl max-h-[80vh] rounded-lg border overflow-hidden ${
            darkMode 
              ? 'bg-gray-800 border-gray-700' 
              : 'bg-white border-gray-200'
          }`}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className={`p-4 border-b ${
            darkMode ? 'border-gray-700' : 'border-gray-200'
          }`}>
            <div className="flex items-center justify-between">
              <h3 className={`text-lg font-semibold ${
                darkMode ? 'text-gray-100' : 'text-gray-900'
              }`}>
                Edit Device Mapping
              </h3>
              <button
                onClick={onCancel}
                className={`p-1 rounded hover:bg-opacity-20 ${
                  darkMode 
                    ? 'text-gray-400 hover:bg-gray-700' 
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <p className={`text-sm mt-1 ${
              darkMode ? 'text-gray-400' : 'text-gray-600'
            }`}>
              Change mapping for <span className="font-medium">{friendlyName}</span>
            </p>
            <div className={`text-xs mt-2 p-2 rounded ${
              darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-700'
            }`}>
              Current: <code className="font-mono">{currentEntityId}</code>
            </div>
          </div>

          {/* Search */}
          <div className={`p-4 border-b ${
            darkMode ? 'border-gray-700' : 'border-gray-200'
          }`}>
            <input
              type="text"
              placeholder="Search entities by name or ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className={`w-full px-3 py-2 rounded border ${
                darkMode
                  ? 'bg-gray-700 border-gray-600 text-gray-100 placeholder-gray-400'
                  : 'bg-white border-gray-300 text-gray-900 placeholder-gray-500'
              } focus:outline-none focus:ring-2 focus:ring-blue-500`}
            />
          </div>

          {/* Content */}
          <div className="p-4 overflow-y-auto max-h-[50vh]">
            {error && (
              <div className={`p-3 mb-4 rounded bg-red-100 border border-red-300 text-red-800 ${
                darkMode ? 'bg-red-900 border-red-700 text-red-200' : ''
              }`}>
                {error}
              </div>
            )}

            {loading ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                <span className={`ml-3 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  Loading entities...
                </span>
              </div>
            ) : entities.length === 0 ? (
              <div className={`text-center py-8 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                No entities found. Try a different search term.
              </div>
            ) : (
              <div className="space-y-2">
                {entities.map((entity) => {
                  const isSelected = entity.entity_id === selectedEntityId;
                  const isCurrent = entity.entity_id === currentEntityId;
                  
                  return (
                    <button
                      key={entity.entity_id}
                      onClick={() => handleEntitySelect(entity.entity_id)}
                      className={`w-full text-left p-3 rounded-lg border transition-all ${
                        isSelected
                          ? darkMode
                            ? 'bg-blue-900 border-blue-600'
                            : 'bg-blue-50 border-blue-500'
                          : darkMode
                            ? 'bg-gray-700 border-gray-600 hover:bg-gray-600'
                            : 'bg-white border-gray-200 hover:bg-gray-50'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className={`font-medium ${
                              darkMode ? 'text-gray-100' : 'text-gray-900'
                            }`}>
                              {entity.friendly_name}
                            </span>
                            {isCurrent && (
                              <span className={`text-xs px-2 py-0.5 rounded ${
                                darkMode ? 'bg-gray-600 text-gray-200' : 'bg-gray-200 text-gray-700'
                              }`}>
                                Current
                              </span>
                            )}
                            {isSelected && !isCurrent && (
                              <span className="text-xs px-2 py-0.5 rounded bg-blue-600 text-white">
                                Selected
                              </span>
                            )}
                          </div>
                          <code className={`text-xs mt-1 block ${
                            darkMode ? 'text-gray-400' : 'text-gray-600'
                          }`}>
                            {entity.entity_id}
                          </code>
                          {entity.capabilities && entity.capabilities.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-2">
                              {entity.capabilities.map((cap) => (
                                <span
                                  key={cap}
                                  className={`text-xs px-2 py-0.5 rounded ${
                                    darkMode
                                      ? 'bg-gray-600 text-gray-300'
                                      : 'bg-gray-100 text-gray-700'
                                  }`}
                                >
                                  {cap}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                        <div className={`ml-3 ${
                          isSelected ? 'text-blue-500' : darkMode ? 'text-gray-500' : 'text-gray-400'
                        }`}>
                          {isSelected ? (
                            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                            </svg>
                          ) : (
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                          )}
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className={`p-4 border-t flex justify-end gap-2 ${
            darkMode ? 'border-gray-700' : 'border-gray-200'
          }`}>
            <button
              onClick={onCancel}
              className={`px-4 py-2 rounded font-medium transition-colors ${
                darkMode
                  ? 'bg-gray-700 text-gray-200 hover:bg-gray-600'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={selectedEntityId === currentEntityId}
              className={`px-4 py-2 rounded font-medium transition-colors ${
                selectedEntityId === currentEntityId
                  ? darkMode
                    ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                    : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                  : 'bg-blue-600 text-white hover:bg-blue-700'
              }`}
            >
              Save Mapping
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};
