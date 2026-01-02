/**
 * Automation Preview Component
 * Epic AI-20 Story AI20.10: Automation Preview & Creation
 * 
 * Displays automation YAML with syntax highlighting and allows creation/editing
 */

import React, { useState, useMemo, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus, vs } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { ToolCall } from '../../services/haAiAgentApi';
import { executeToolCall } from '../../services/haAiAgentApi';
import { apiV2 } from '../../services/api-v2';
import toast from 'react-hot-toast';
import { DebugTab } from './DebugTab';

interface AutomationPreviewProps {
  automationYaml: string;
  alias?: string;
  toolCall?: ToolCall;
  darkMode: boolean;
  onClose: () => void;
  onEdit?: (yaml: string) => void;
  conversationId: string;
  originalPrompt?: string; // Optional: original user prompt for fallback
}

interface ParsedAutomation {
  alias?: string;
  description?: string;
  entities: string[];
  trigger?: Record<string, unknown>;
  action?: Record<string, unknown>;
}

export const AutomationPreview: React.FC<AutomationPreviewProps> = ({
  automationYaml,
  alias: providedAlias,
  toolCall,
  darkMode,
  onClose,
  onEdit,
  conversationId,
  originalPrompt,
}) => {
  const [isCreating, setIsCreating] = useState(false);
  const [createdAutomationId, setCreatedAutomationId] = useState<string | null>(null);
  const [validationResult, setValidationResult] = useState<{
    valid: boolean;
    errors: string[];
    warnings: string[];
    score: number;
    fixed_yaml?: string;
    fixes_applied?: string[];
    isNetworkError?: boolean;
  } | null>(null);
  const [isValidating, setIsValidating] = useState(false);
  const [showNormalizedYaml, setShowNormalizedYaml] = useState(false);
  const [activeTab, setActiveTab] = useState<'preview' | 'debug'>('preview');

  // Parse automation YAML to extract metadata (using regex since YAML isn't JSON)
  const parsedAutomation = useMemo<ParsedAutomation>(() => {
    const cleanYaml = automationYaml.replace(/```yaml\n?/g, '').replace(/```\n?/g, '').trim();
    const entities: string[] = [];
    
    // Extract alias
    const aliasMatch = cleanYaml.match(/alias:\s*['"]?([^'\n"]+)['"]?/i);
    const alias = aliasMatch ? aliasMatch[1] : providedAlias;
    
    // Extract description
    const descMatch = cleanYaml.match(/description:\s*['"]?([^'\n"]+)['"]?/i);
    const description = descMatch ? descMatch[1] : undefined;
    
    // Extract entities from entity_id patterns
    const entityMatches = cleanYaml.matchAll(/entity_id:\s*['"]?([^'\n"]+)['"]?/gi);
    for (const match of entityMatches) {
      if (match[1]) {
        entities.push(match[1]);
      }
    }
    
    // Also check for target.entity_id patterns
    const targetEntityMatches = cleanYaml.matchAll(/target:\s*\n\s*entity_id:\s*['"]?([^'\n"]+)['"]?/gi);
    for (const match of targetEntityMatches) {
      if (match[1]) {
        entities.push(match[1]);
      }
    }

    return {
      alias,
      description,
      entities: [...new Set(entities)], // Remove duplicates
    };
  }, [automationYaml, providedAlias]);

  // Clean YAML for display (remove markdown code blocks)
  const cleanYaml = useMemo(() => {
    return automationYaml
      .replace(/```yaml\n?/g, '')
      .replace(/```\n?/g, '')
      .trim();
  }, [automationYaml]);

  // Validate YAML on mount and when YAML changes (Epic 51, Story 51.9)
  useEffect(() => {
    const validateYAML = async () => {
      if (!cleanYaml) return;
      
      setIsValidating(true);
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/c118a7ab-8e77-4e17-97b9-a6f65423f981',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'AutomationPreview.tsx:110',message:'validateYAML started',data:{cleanYamlLength:cleanYaml.length,cleanYamlPreview:cleanYaml.substring(0,100)},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A,B'})}).catch(()=>{});
      // #endregion
      try {
        const result = await apiV2.validateYAML(cleanYaml, {
          normalize: true,
          validateEntities: true,
          validateServices: false,
        });
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/c118a7ab-8e77-4e17-97b9-a6f65423f981',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'AutomationPreview.tsx:118',message:'Validation succeeded',data:{valid:result.valid,score:result.score,errorsCount:result.errors.length,warningsCount:result.warnings.length,hasFixedYaml:!!result.fixed_yaml},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
        // #endregion
        setValidationResult(result);
        
        // If fixes were applied, show normalized YAML by default
        if (result.fixed_yaml && result.fixes_applied && result.fixes_applied.length > 0) {
          setShowNormalizedYaml(true);
        }
      } catch (error) {
        console.error('Failed to validate YAML:', error);
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/c118a7ab-8e77-4e17-97b9-a6f65423f981',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'AutomationPreview.tsx:129',message:'Validation error caught',data:{errorType:error?.constructor?.name,errorMessage:error instanceof Error ? error.message : String(error),errorName:error instanceof Error ? error.name : 'unknown',hasStack:error instanceof Error ? !!error.stack : false},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A,C,D'})}).catch(()=>{});
        // #endregion
        // Extract error message for better user feedback
        let errorMessage = 'Failed to validate automation YAML';
        let isNetworkError = false;
        if (error instanceof Error) {
          errorMessage = error.message || errorMessage;
          // Detect network errors (CORS, connection refused, etc.)
          isNetworkError = errorMessage.includes('Failed to fetch') || 
                          errorMessage.includes('Network error') ||
                          errorMessage.includes('fetch') ||
                          error.name === 'TypeError';
        } else if (typeof error === 'object' && error !== null && 'message' in error) {
          errorMessage = String(error.message);
        }
        
        if (isNetworkError) {
          toast.error('Validation service unavailable. You can still create the automation, but it won\'t be validated.', {
            icon: '⚠️',
            duration: 5000,
          });
        } else {
          toast.error(errorMessage);
        }
        
        // Set validation result to show error state even on exception
        // For network errors, we allow creation (valid: true but with warnings)
        // For validation errors, we block creation (valid: false)
        const errorResult = {
          valid: isNetworkError, // Allow creation on network errors
          errors: isNetworkError ? [] : [errorMessage],
          warnings: isNetworkError ? ['Validation service unavailable - automation not validated'] : [],
          score: 0,
          isNetworkError,
        };
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/c118a7ab-8e77-4e17-97b9-a6f65423f981',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'AutomationPreview.tsx:152',message:'Setting error validation result',data:{valid:errorResult.valid,isNetworkError:errorResult.isNetworkError,errorsCount:errorResult.errors.length,warningsCount:errorResult.warnings.length},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'E'})}).catch(()=>{});
        // #endregion
        setValidationResult(errorResult);
      } finally {
        setIsValidating(false);
      }
    };

    validateYAML();
  }, [cleanYaml]);

  // Use normalized YAML if available and user wants to see it
  const yamlToDisplay = useMemo(() => {
    if (showNormalizedYaml && validationResult?.fixed_yaml) {
      return validationResult.fixed_yaml;
    }
    return cleanYaml;
  }, [cleanYaml, showNormalizedYaml, validationResult]);

  const handleCreateAutomation = async () => {
    if (!parsedAutomation.alias) {
      toast.error('Automation alias is required');
      return;
    }

    setIsCreating(true);
    try {
      // Determine user_prompt: Use the actual prompt from toolCall.arguments (which is what the AI agent used, 
      // whether original or enhanced), then fall back to originalPrompt prop, then description/alias
      const userPrompt = toolCall?.arguments?.user_prompt?.trim() 
        || originalPrompt?.trim() 
        || parsedAutomation.description?.trim() 
        || parsedAutomation.alias?.trim() 
        || 'Automation creation request';

      // Execute create_automation_from_prompt tool call
      const result = await executeToolCall({
        tool_name: 'create_automation_from_prompt',
        arguments: {
          user_prompt: userPrompt,
          automation_yaml: cleanYaml,
          alias: parsedAutomation.alias,
        },
      });

      if (result.success) {
        setCreatedAutomationId(result.automation_id || null);
        toast.success(`Automation "${parsedAutomation.alias}" created successfully!`, {
          icon: '✅',
        });
      } else {
        toast.error(result.error || 'Failed to create automation', {
          icon: '❌',
        });
      }
    } catch (error) {
      console.error('Failed to create automation:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to create automation';
      toast.error(errorMessage, {
        icon: '❌',
      });
    } finally {
      setIsCreating(false);
    }
  };

  const handleEdit = () => {
    if (onEdit) {
      onEdit(cleanYaml);
      onClose();
    }
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0, y: 20 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.9, opacity: 0, y: 20 }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          className={`rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col ${
            darkMode ? 'bg-gray-800' : 'bg-white'
          }`}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div
            className={`px-6 py-4 border-b flex items-center justify-between ${
              darkMode ? 'border-gray-700' : 'border-gray-200'
            }`}
          >
            <div>
              <h2 className={`text-xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                ⚙️ Automation Preview
              </h2>
              {parsedAutomation.alias && (
                <p className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  {parsedAutomation.alias}
                </p>
              )}
            </div>
            <button
              onClick={onClose}
              className={`p-2 rounded-md transition-colors ${
                darkMode ? 'text-gray-400 hover:bg-gray-700' : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              ✕
            </button>
          </div>

          {/* Metadata */}
          {parsedAutomation.description && (
            <div className={`px-6 py-3 border-b ${darkMode ? 'border-gray-700 bg-gray-750' : 'border-gray-200 bg-gray-50'}`}>
              <p className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                <span className="font-medium">Description:</span> {parsedAutomation.description}
              </p>
            </div>
          )}

          {parsedAutomation.entities.length > 0 && (
            <div className={`px-6 py-3 border-b ${darkMode ? 'border-gray-700 bg-gray-750' : 'border-gray-200 bg-gray-50'}`}>
              <p className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                <span className="font-medium">Entities:</span>{' '}
                {parsedAutomation.entities.join(', ')}
              </p>
            </div>
          )}

          {/* Validation Feedback Panel (Epic 51, Story 51.9) */}
          {validationResult && (
            <div className={`px-6 py-3 border-b ${
              darkMode ? 'border-gray-700' : 'border-gray-200'
            } ${
              validationResult.valid
                ? darkMode ? 'bg-green-900/20' : 'bg-green-50'
                : darkMode ? 'bg-red-900/20' : 'bg-red-50'
            }`}>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  {isValidating ? (
                    <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                      🔄 Validating...
                    </span>
                  ) : validationResult.isNetworkError ? (
                    <span className={`text-sm font-medium ${darkMode ? 'text-yellow-400' : 'text-yellow-700'}`}>
                      ⚠️ Validation Unavailable (Network Error)
                    </span>
                  ) : validationResult.valid ? (
                    <span className={`text-sm font-medium ${darkMode ? 'text-green-400' : 'text-green-700'}`}>
                      ✅ Valid (Score: {validationResult.score.toFixed(1)}/100)
                    </span>
                  ) : (
                    <span className={`text-sm font-medium ${darkMode ? 'text-red-400' : 'text-red-700'}`}>
                      ❌ Invalid (Score: {validationResult.score.toFixed(1)}/100)
                    </span>
                  )}
                </div>
                {validationResult.fixed_yaml && validationResult.fixes_applied && validationResult.fixes_applied.length > 0 && (
                  <button
                    onClick={() => setShowNormalizedYaml(!showNormalizedYaml)}
                    className={`text-xs px-2 py-1 rounded ${
                      darkMode
                        ? 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                    }`}
                  >
                    {showNormalizedYaml ? 'Show Original' : 'Show Fixed YAML'}
                  </button>
                )}
              </div>
              
              {validationResult.errors.length > 0 && (
                <div className="mb-2">
                  <p className={`text-xs font-medium mb-1 ${darkMode ? 'text-red-400' : 'text-red-700'}`}>
                    Errors ({validationResult.errors.length}):
                  </p>
                  <ul className={`text-xs list-disc list-inside space-y-1 ${
                    darkMode ? 'text-red-300' : 'text-red-600'
                  }`}>
                    {validationResult.errors.map((error, idx) => (
                      <li key={idx}>{error}</li>
                    ))}
                  </ul>
                </div>
              )}
              
              {validationResult.warnings.length > 0 && (
                <div className="mb-2">
                  <p className={`text-xs font-medium mb-1 ${darkMode ? 'text-yellow-400' : 'text-yellow-700'}`}>
                    Warnings ({validationResult.warnings.length}):
                  </p>
                  <ul className={`text-xs list-disc list-inside space-y-1 ${
                    darkMode ? 'text-yellow-300' : 'text-yellow-600'
                  }`}>
                    {validationResult.warnings.map((warning, idx) => (
                      <li key={idx}>{warning}</li>
                    ))}
                  </ul>
                </div>
              )}
              
              {validationResult.fixes_applied && validationResult.fixes_applied.length > 0 && (
                <div>
                  <p className={`text-xs font-medium mb-1 ${darkMode ? 'text-blue-400' : 'text-blue-700'}`}>
                    Auto-Fixes Applied ({validationResult.fixes_applied.length}):
                  </p>
                  <ul className={`text-xs list-disc list-inside space-y-1 ${
                    darkMode ? 'text-blue-300' : 'text-blue-600'
                  }`}>
                    {validationResult.fixes_applied.map((fix, idx) => (
                      <li key={idx}>{fix}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Tab Navigation */}
          <div 
            className={`border-b flex gap-1 px-6 ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}
            role="tablist"
            aria-label="Automation preview tabs"
          >
            <button
              onClick={() => setActiveTab('preview')}
              role="tab"
              aria-selected={activeTab === 'preview'}
              aria-controls="preview-tabpanel"
              id="preview-tab"
              className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
                activeTab === 'preview'
                  ? darkMode
                    ? 'border-blue-500 text-blue-400'
                    : 'border-blue-600 text-blue-600'
                  : darkMode
                  ? 'border-transparent text-gray-400 hover:text-gray-300'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              Preview
            </button>
            <button
              onClick={() => setActiveTab('debug')}
              role="tab"
              aria-selected={activeTab === 'debug'}
              aria-controls="debug-tabpanel"
              id="debug-tab"
              className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
                activeTab === 'debug'
                  ? darkMode
                    ? 'border-blue-500 text-blue-400'
                    : 'border-blue-600 text-blue-600'
                  : darkMode
                  ? 'border-transparent text-gray-400 hover:text-gray-300'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              🐛 Debug
            </button>
          </div>

          {/* Tab Content */}
          <div className="flex-1 overflow-hidden flex flex-col min-h-0">
            {activeTab === 'preview' ? (
              <div 
                className="flex-1 overflow-auto p-6"
                role="tabpanel"
                id="preview-tabpanel"
                aria-labelledby="preview-tab"
              >
                <div className="rounded-lg overflow-hidden border border-gray-300">
                  <SyntaxHighlighter
                    language="yaml"
                    style={darkMode ? vscDarkPlus : vs}
                    customStyle={{
                      margin: 0,
                      padding: '1rem',
                      fontSize: '0.875rem',
                      lineHeight: '1.5',
                    }}
                    showLineNumbers
                  >
                    {yamlToDisplay}
                  </SyntaxHighlighter>
                </div>
              </div>
            ) : (
              <div 
                className="flex-1 overflow-hidden min-h-0"
                role="tabpanel"
                id="debug-tabpanel"
                aria-labelledby="debug-tab"
              >
                <DebugTab
                  conversationId={conversationId || null}
                  darkMode={darkMode}
                />
              </div>
            )}
          </div>

          {/* Footer Actions */}
          <div
            className={`px-6 py-4 border-t flex items-center justify-between gap-3 ${
              darkMode ? 'border-gray-700' : 'border-gray-200'
            }`}
          >
            <div className="flex gap-2">
              {onEdit && (
                <button
                  onClick={handleEdit}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                    darkMode
                      ? 'bg-gray-700 text-white hover:bg-gray-600'
                      : 'bg-gray-200 text-gray-900 hover:bg-gray-300'
                  }`}
                >
                  Edit
                </button>
              )}
            </div>
            <div className="flex gap-2">
              <button
                onClick={onClose}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  darkMode
                    ? 'bg-gray-700 text-white hover:bg-gray-600'
                    : 'bg-gray-200 text-gray-900 hover:bg-gray-300'
                }`}
              >
                Cancel
              </button>
              {!createdAutomationId ? (
                <button
                  onClick={() => {
                    // #region agent log
                    fetch('http://127.0.0.1:7242/ingest/c118a7ab-8e77-4e17-97b9-a6f65423f981',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'AutomationPreview.tsx:476',message:'Create button clicked',data:{isCreating,hasAlias:!!parsedAutomation.alias,validationValid:validationResult?.valid,isNetworkError:validationResult?.isNetworkError,isValidating},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'E'})}).catch(()=>{});
                    // #endregion
                    handleCreateAutomation();
                  }}
                  disabled={
                    isCreating ||
                    !parsedAutomation.alias ||
                    (validationResult && !validationResult.valid && !validationResult.isNetworkError) ||
                    isValidating
                  }
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                    isCreating || !parsedAutomation.alias || (validationResult && !validationResult.valid && !validationResult.isNetworkError) || isValidating
                      ? 'bg-gray-400 cursor-not-allowed'
                      : darkMode
                      ? 'bg-blue-600 text-white hover:bg-blue-700'
                      : 'bg-blue-500 text-white hover:bg-blue-600'
                  }`}
                  title={
                    validationResult && !validationResult.valid && !validationResult.isNetworkError
                      ? 'Fix validation errors before creating automation'
                      : validationResult?.isNetworkError
                      ? 'Validation service unavailable - automation will be created without validation'
                      : undefined
                  }
                >
                  {isCreating
                    ? 'Creating...'
                    : isValidating
                    ? 'Validating...'
                    : validationResult && !validationResult.valid && !validationResult.isNetworkError
                    ? 'Fix Errors First'
                    : 'Create Automation'}
                </button>
              ) : (
                <div className="flex items-center gap-2">
                  <span className={`text-sm ${darkMode ? 'text-green-400' : 'text-green-600'}`}>
                    ✅ Created
                  </span>
                  {createdAutomationId && (
                    <a
                      href={`/deployed#${createdAutomationId}`}
                      className={`text-sm underline ${darkMode ? 'text-blue-400' : 'text-blue-600'}`}
                    >
                      View Automation
                    </a>
                  )}
                </div>
              )}
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

