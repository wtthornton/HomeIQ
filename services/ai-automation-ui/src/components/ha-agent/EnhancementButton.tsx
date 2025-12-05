/**
 * Enhancement Button Component
 * 
 * Button that appears next to Send button when automation preview is shown.
 * Generates 5 enhancement suggestions (small, medium, large, advanced, fun).
 */
import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { executeToolCall, type Enhancement } from '../../services/haAiAgentApi';
import toast from 'react-hot-toast';

interface EnhancementButtonProps {
  automationYaml: string;
  originalPrompt: string;
  conversationId: string;
  darkMode: boolean;
  onEnhancementSelected: (enhancement: Enhancement) => void;
}

export const EnhancementButton: React.FC<EnhancementButtonProps> = ({
  automationYaml,
  originalPrompt,
  conversationId,
  darkMode,
  onEnhancementSelected,
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [enhancements, setEnhancements] = useState<Enhancement[] | null>(null);
  const [showModal, setShowModal] = useState(false);

  const handleEnhance = async () => {
    setIsLoading(true);
    setShowModal(true);
    
    // Add timeout (60 seconds)
    const timeoutPromise = new Promise((_, reject) => {
      setTimeout(() => reject(new Error('Enhancement generation timed out after 60 seconds')), 60000);
    });
    
    try {
      const result = await Promise.race([
        executeToolCall({
          tool_name: 'suggest_automation_enhancements',
          arguments: {
            automation_yaml: automationYaml,
            original_prompt: originalPrompt,
            conversation_id: conversationId,
          },
        }),
        timeoutPromise
      ]) as any;

      if (result.success && result.enhancements) {
        setEnhancements(result.enhancements);
        toast.success('Enhancements generated!', { icon: '✨' });
      } else {
        toast.error(result.error || 'Failed to generate enhancements', { icon: '❌' });
        setShowModal(false);
      }
    } catch (error: any) {
      console.error('Error generating enhancements:', error);
      const errorMessage = error.message?.includes('timed out') 
        ? 'Enhancement generation timed out. Please try again.'
        : 'Failed to generate enhancements';
      toast.error(errorMessage, { icon: '❌', duration: 5000 });
      setShowModal(false);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectEnhancement = (enhancement: Enhancement) => {
    onEnhancementSelected(enhancement);
    setShowModal(false);
    toast.success(`Applied ${enhancement.title}`, { icon: '✅' });
  };

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'small':
        return darkMode ? 'bg-green-600 hover:bg-green-700' : 'bg-green-500 hover:bg-green-600';
      case 'medium':
        return darkMode ? 'bg-blue-600 hover:bg-blue-700' : 'bg-blue-500 hover:bg-blue-600';
      case 'large':
        return darkMode ? 'bg-purple-600 hover:bg-purple-700' : 'bg-purple-500 hover:bg-purple-600';
      case 'advanced':
        return darkMode ? 'bg-orange-600 hover:bg-orange-700' : 'bg-orange-500 hover:bg-orange-600';
      case 'fun':
        return darkMode ? 'bg-pink-600 hover:bg-pink-700' : 'bg-pink-500 hover:bg-pink-600';
      default:
        return darkMode ? 'bg-gray-600 hover:bg-gray-700' : 'bg-gray-500 hover:bg-gray-600';
    }
  };

  const getLevelIcon = (level: string) => {
    switch (level) {
      case 'small':
        return '🔧';
      case 'medium':
        return '⚙️';
      case 'large':
        return '🚀';
      case 'advanced':
        return '📊';
      case 'fun':
        return '🎉';
      default:
        return '✨';
    }
  };

  const getSourceBadge = (source: string, patternId?: number, synergyId?: string) => {
    if (source === 'pattern' && patternId) {
      return (
        <span className="text-xs px-2 py-1 rounded bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
          📊 Pattern #{patternId}
        </span>
      );
    }
    if (source === 'synergy' && synergyId) {
      return (
        <span className="text-xs px-2 py-1 rounded bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200">
          🔗 Synergy
        </span>
      );
    }
    return null;
  };

  return (
    <>
      <button
        onClick={handleEnhance}
        disabled={isLoading}
        className={`px-4 py-2 rounded-lg font-medium transition-colors min-h-[44px] flex items-center gap-2 ${
          isLoading
            ? darkMode
              ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
              : 'bg-gray-200 text-gray-400 cursor-not-allowed'
            : darkMode
            ? 'bg-purple-600 text-white hover:bg-purple-700'
            : 'bg-purple-500 text-white hover:bg-purple-600'
        }`}
        title="Generate enhancement suggestions"
      >
        {isLoading ? (
          <>
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
            <span>Enhancing...</span>
          </>
        ) : (
          <>
            <span>✨</span>
            <span>Enhance</span>
          </>
        )}
      </button>

      <AnimatePresence>
        {showModal && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
            onClick={() => setShowModal(false)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              onClick={(e) => e.stopPropagation()}
              className={`max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto rounded-lg ${
                darkMode ? 'bg-gray-800' : 'bg-white'
              } shadow-xl`}
            >
              <div className={`p-6 border-b ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
                <div className="flex items-center justify-between">
                  <h2 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    ✨ Enhancement Suggestions
                  </h2>
                  <button
                    onClick={() => setShowModal(false)}
                    className={`text-2xl ${darkMode ? 'text-gray-400 hover:text-white' : 'text-gray-500 hover:text-gray-900'}`}
                  >
                    ×
                  </button>
                </div>
                <p className={`mt-2 text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  Choose an enhancement to apply to your automation
                </p>
              </div>

              <div className="p-6">
                {isLoading ? (
                  <div className="flex items-center justify-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
                    <span className={`ml-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                      Generating enhancements...
                    </span>
                  </div>
                ) : enhancements ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {enhancements.map((enhancement, index) => (
                      <motion.div
                        key={index}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.1 }}
                        className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                          darkMode
                            ? 'border-gray-700 bg-gray-700 hover:border-purple-500'
                            : 'border-gray-200 bg-gray-50 hover:border-purple-500'
                        }`}
                        onClick={() => handleSelectEnhancement(enhancement)}
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <span className="text-2xl">{getLevelIcon(enhancement.level)}</span>
                            <h3 className={`font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                              {enhancement.title}
                            </h3>
                          </div>
                          {getSourceBadge(enhancement.source, enhancement.pattern_id, enhancement.synergy_id)}
                        </div>
                        <p className={`text-sm mb-3 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                          {enhancement.description}
                        </p>
                        <div className="space-y-1">
                          {enhancement.changes.map((change, i) => (
                            <div
                              key={i}
                              className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}
                            >
                              • {change}
                            </div>
                          ))}
                        </div>
                        <div className="mt-3 pt-3 border-t border-gray-600">
                          <span
                            className={`text-xs font-medium px-2 py-1 rounded ${getLevelColor(enhancement.level)} text-white`}
                          >
                            {enhancement.level.toUpperCase()}
                          </span>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                ) : null}
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  );
};

