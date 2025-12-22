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
  automationYaml?: string;  // Optional - only needed for YAML enhancement mode
  originalPrompt: string;   // Required
  conversationId: string;   // Required
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
  const [enhancementMode, setEnhancementMode] = useState<'prompt' | 'yaml' | null>(null);

  const handleEnhance = async () => {
    if (!conversationId) {
      toast.error('No conversation active. Please start a conversation first.', { icon: '❌' });
      return;
    }
    
    if (!originalPrompt) {
      toast.error('Original prompt is required for enhancements.', { icon: '❌' });
      return;
    }
    
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
            automation_yaml: automationYaml || undefined,  // Optional
            original_prompt: originalPrompt,
            conversation_id: conversationId,
          },
        }),
        timeoutPromise
      ]) as any;

      if (result.success && result.enhancements && Array.isArray(result.enhancements) && result.enhancements.length > 0) {
        setEnhancements(result.enhancements);
        setEnhancementMode(result.mode || (automationYaml ? 'yaml' : 'prompt'));
        toast.success('Enhancements generated!', { icon: '✨' });
      } else {
        console.error('Enhancement API response:', result);
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

  // Check prerequisites
  const hasPrerequisites = !!(originalPrompt && conversationId);
  const missingPrerequisites: string[] = [];
  if (!conversationId) missingPrerequisites.push('active conversation');
  if (!originalPrompt) missingPrerequisites.push('original prompt');
  // Note: automationYaml is optional - enhancement works with or without it

  return (
    <>
      <div className="relative">
        <button
          onClick={handleEnhance}
          disabled={isLoading || !hasPrerequisites}
          className={`px-4 py-2 rounded-lg font-medium transition-colors min-h-[44px] flex items-center gap-2 relative ${
            isLoading
              ? darkMode
                ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                : 'bg-gray-200 text-gray-400 cursor-not-allowed'
              : !hasPrerequisites
              ? darkMode
                ? 'bg-gray-700 text-gray-500 cursor-not-allowed border-2 border-yellow-600'
                : 'bg-gray-200 text-gray-400 cursor-not-allowed border-2 border-yellow-500'
              : darkMode
              ? 'bg-purple-600 text-white hover:bg-purple-700'
              : 'bg-purple-500 text-white hover:bg-purple-600'
          }`}
          aria-label={
            hasPrerequisites
              ? 'Generate enhancement suggestions'
              : `Enhancement button disabled. Missing: ${missingPrerequisites.join(', ')}`
          }
          aria-busy={isLoading}
          aria-disabled={isLoading || !hasPrerequisites}
          title={
            hasPrerequisites
              ? 'Generate enhancement suggestions'
              : `Missing: ${missingPrerequisites.join(', ')}`
          }
        >
          {isLoading ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              <span>Enhancing...</span>
            </>
          ) : !hasPrerequisites ? (
            <>
              <span>⚠️</span>
              <span>Enhance</span>
            </>
          ) : (
            <>
              <span>✨</span>
              <span>Enhance</span>
            </>
          )}
        </button>
        
        {/* Persistent warning tooltip when prerequisites missing */}
        {!hasPrerequisites && !isLoading && (
          <div
            className={`absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 rounded-lg text-xs whitespace-nowrap z-50 ${
              darkMode
                ? 'bg-yellow-900 border border-yellow-700 text-yellow-200'
                : 'bg-yellow-50 border border-yellow-300 text-yellow-800'
            } shadow-lg`}
            role="tooltip"
            aria-live="polite"
            aria-atomic="true"
          >
            <div className="flex items-center gap-2">
              <span aria-hidden="true">⚠️</span>
              <span>Missing: {missingPrerequisites.join(', ')}</span>
            </div>
            <div
              className={`absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 ${
                darkMode ? 'border-t-yellow-900' : 'border-t-yellow-50'
              }`}
              aria-hidden="true"
            />
          </div>
        )}
      </div>

      <AnimatePresence mode="wait">
        {showModal && (
          <div
            className="fixed inset-0 z-[9999] flex items-center justify-center bg-black bg-opacity-50 backdrop-blur-sm"
            onClick={() => setShowModal(false)}
            style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0 }}
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
                    {enhancementMode && (
                      <span className={`ml-2 text-sm font-normal ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                        ({enhancementMode === 'prompt' ? 'Prompt Enhancement' : 'YAML Enhancement'})
                      </span>
                    )}
                  </h2>
                  <button
                    onClick={() => setShowModal(false)}
                    className={`text-2xl ${darkMode ? 'text-gray-400 hover:text-white' : 'text-gray-500 hover:text-gray-900'}`}
                  >
                    ×
                  </button>
                </div>
                <p className={`mt-2 text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  {enhancementMode === 'prompt' 
                    ? 'Choose an enhanced prompt to use for generating your automation'
                    : 'Choose an enhancement to apply to your automation'}
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
                ) : enhancements && enhancements.length > 0 ? (
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
                ) : (
                  <div className="flex items-center justify-center py-12">
                    <p className={`${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                      No enhancements available. Please try again.
                    </p>
                  </div>
                )}
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  );
};

