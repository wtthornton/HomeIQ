/**
 * Enhanced Batch Actions Component
 * Select multiple suggestions and perform bulk operations with confirmation modals
 */

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { BatchActionModal } from './BatchActionModal';

interface BatchActionsProps {
  selectedCount: number;
  onApproveAll: () => void;
  onRejectAll: () => void;
  onExport: () => void;
  onClearSelection: () => void;
  darkMode?: boolean;
  keyboardShortcuts?: {
    selectAll: string;
    approve: string;
    reject: string;
    clear: string;
  };
}

export const BatchActions: React.FC<BatchActionsProps> = ({
  selectedCount,
  onApproveAll,
  onRejectAll,
  onExport,
  onClearSelection,
  darkMode = false,
  keyboardShortcuts
}) => {
  const [showApproveModal, setShowApproveModal] = useState(false);
  const [showRejectModal, setShowRejectModal] = useState(false);

  if (selectedCount === 0) return null;

  const handleApproveConfirm = async () => {
    await onApproveAll();
    setShowApproveModal(false);
  };

  const handleRejectConfirm = async () => {
    await onRejectAll();
    setShowRejectModal(false);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className={`sticky top-16 z-40 p-3 border ${darkMode ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-gray-50'}`}
    >
      <div className="flex items-center justify-between">
        <div className={`text-sm font-medium ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          {selectedCount} selected
          {keyboardShortcuts && (
            <span className={`ml-2 text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
              ({keyboardShortcuts.approve} approve, {keyboardShortcuts.reject} reject)
            </span>
          )}
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => setShowApproveModal(true)}
            className="px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-sm font-medium transition-colors"
          >
            Approve All
          </button>

          <button
            onClick={() => setShowRejectModal(true)}
            className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white text-sm font-medium transition-colors"
          >
            Reject All
          </button>

          <button
            onClick={onExport}
            className={`px-3 py-1 text-sm font-medium transition-colors ${
              darkMode
                ? 'bg-gray-700 hover:bg-gray-600 text-white'
                : 'bg-gray-200 hover:bg-gray-300 text-gray-900'
            }`}
          >
            Export
          </button>

          <button
            onClick={onClearSelection}
            className={`px-3 py-1 text-sm font-medium transition-colors ${
              darkMode
                ? 'bg-gray-700 hover:bg-gray-600 text-white'
                : 'bg-gray-200 hover:bg-gray-300 text-gray-900'
            }`}
          >
            Clear
          </button>
        </div>
      </div>

      {/* Approval Confirmation Modal */}
      <BatchActionModal
        isOpen={showApproveModal}
        onClose={() => setShowApproveModal(false)}
        onConfirm={handleApproveConfirm}
        title="Approve Selected Suggestions"
        message="Are you sure you want to approve these automation suggestions? They will be ready for deployment to Home Assistant."
        confirmLabel="Approve All"
        cancelLabel="Cancel"
        variant="approve"
        selectedCount={selectedCount}
        darkMode={darkMode}
      />

      {/* Rejection Confirmation Modal */}
      <BatchActionModal
        isOpen={showRejectModal}
        onClose={() => setShowRejectModal(false)}
        onConfirm={handleRejectConfirm}
        title="Reject Selected Suggestions"
        message="Are you sure you want to reject these automation suggestions? This action cannot be undone."
        confirmLabel="Reject All"
        cancelLabel="Cancel"
        variant="reject"
        selectedCount={selectedCount}
        darkMode={darkMode}
      />
    </motion.div>
  );
};

