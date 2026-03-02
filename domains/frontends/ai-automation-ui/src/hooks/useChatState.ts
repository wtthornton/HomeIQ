/**
 * useChatState Hook
 * Encapsulates chat state declarations for HAAgentChat.
 * Extracted to reduce the monolithic component's state block.
 */

import { useState, useRef } from 'react';
import type { Conversation, Message, ToolCall } from '../services/haAiAgentApi';

export interface ChatMessage extends Message {
  isLoading?: boolean;
  error?: string;
  toolCalls?: ToolCall[];
  responseTimeMs?: number;
}

export function useChatState() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);
  const [blueprintContext, setBlueprintContext] = useState<any>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleteTargetId, setDeleteTargetId] = useState<string | null>(null);
  const [clearChatModalOpen, setClearChatModalOpen] = useState(false);
  const [automationPreviewOpen, setAutomationPreviewOpen] = useState(false);
  const [previewAutomationYaml, setPreviewAutomationYaml] = useState<string>('');
  const [previewAutomationAlias, setPreviewAutomationAlias] = useState<string | undefined>();
  const [previewToolCall, setPreviewToolCall] = useState<ToolCall | undefined>(undefined);
  const [originalPrompt, setOriginalPrompt] = useState<string>('');
  const [sidebarRefreshTrigger, setSidebarRefreshTrigger] = useState(0);
  const [activeTab, setActiveTab] = useState<'chat' | 'debug'>('chat');
  const [selectedDeviceId, setSelectedDeviceId] = useState<string | null>(null);
  const [devicePickerOpen, setDevicePickerOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  return {
    messages, setMessages,
    inputValue, setInputValue,
    isLoading, setIsLoading,
    currentConversationId, setCurrentConversationId,
    currentConversation, setCurrentConversation,
    isInitializing, setIsInitializing,
    blueprintContext, setBlueprintContext,
    sidebarOpen, setSidebarOpen,
    deleteModalOpen, setDeleteModalOpen,
    deleteTargetId, setDeleteTargetId,
    clearChatModalOpen, setClearChatModalOpen,
    automationPreviewOpen, setAutomationPreviewOpen,
    previewAutomationYaml, setPreviewAutomationYaml,
    previewAutomationAlias, setPreviewAutomationAlias,
    previewToolCall, setPreviewToolCall,
    originalPrompt, setOriginalPrompt,
    sidebarRefreshTrigger, setSidebarRefreshTrigger,
    activeTab, setActiveTab,
    selectedDeviceId, setSelectedDeviceId,
    devicePickerOpen, setDevicePickerOpen,
    messagesEndRef,
    inputRef,
  };
}

/**
 * Deduplicate messages using a Set-based approach.
 * Deduplicates by message_id first (most reliable), then by content+role.
 */
export function deduplicateMessages(messages: ChatMessage[]): ChatMessage[] {
  const seenById = new Set<string>();
  const seenByContent = new Set<string>();
  const uniqueMessages: ChatMessage[] = [];

  for (const msg of messages) {
    if (!msg.content.trim() && msg.isLoading) continue;

    const normalizedContent = msg.content.trim();
    const isTemp = msg.message_id.startsWith('temp-') || msg.message_id.startsWith('loading-');

    if (!isTemp && msg.message_id) {
      const idKey = `id:${msg.message_id}`;
      const contentKey = `content:${msg.role}:${normalizedContent}`;
      if (seenById.has(idKey) || seenByContent.has(contentKey)) continue;
      seenById.add(idKey);
      seenByContent.add(contentKey);
      uniqueMessages.push(msg);
    } else {
      const timestamp = new Date(msg.created_at).getTime();
      const contentKey = `content:${msg.role}:${normalizedContent}:${timestamp}`;
      if (!seenByContent.has(contentKey)) {
        seenByContent.add(contentKey);
        uniqueMessages.push(msg);
      }
    }
  }

  return uniqueMessages.sort((a, b) =>
    new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  );
}
