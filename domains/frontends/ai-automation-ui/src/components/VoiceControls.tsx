/**
 * Voice Controls Component (Story 26.6)
 *
 * Provides microphone button with recording state, visual recording indicator,
 * TTS playback with stop button, and voice component status indicators.
 * Connects to voice-gateway WebSocket at /api/voice/stream.
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';

type VoiceState = 'idle' | 'connecting' | 'listening' | 'recording' | 'processing' | 'speaking' | 'error';

interface ComponentStatus {
  stt: { enabled: boolean; type: string; status: string };
  tts: { enabled: boolean; type: string; status: string };
  wake_word: { enabled: boolean; type: string; status: string };
}

interface VoiceControlsProps {
  gatewayUrl?: string;
  onTranscription?: (text: string) => void;
  onResponse?: (text: string) => void;
  className?: string;
}

const VOICE_GATEWAY_WS = import.meta.env.VITE_VOICE_GATEWAY_WS || 'ws://localhost:8041';
const VOICE_GATEWAY_HTTP = import.meta.env.VITE_VOICE_GATEWAY_HTTP || 'http://localhost:8041';

export const VoiceControls: React.FC<VoiceControlsProps> = ({
  gatewayUrl,
  onTranscription,
  onResponse,
  className = '',
}) => {
  const wsUrl = gatewayUrl || VOICE_GATEWAY_WS;
  const [state, setState] = useState<VoiceState>('idle');
  const [transcription, setTranscription] = useState('');
  const [responseText, setResponseText] = useState('');
  const [componentStatus, setComponentStatus] = useState<ComponentStatus | null>(null);
  const [errorMessage, setErrorMessage] = useState('');

  const wsRef = useRef<WebSocket | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const audioElementRef = useRef<HTMLAudioElement | null>(null);

  // Fetch component status on mount
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch(`${VOICE_GATEWAY_HTTP}/api/admin/status`);
        if (res.ok) {
          const data = await res.json();
          setComponentStatus(data);
        }
      } catch {
        // Voice gateway may not be running
      }
    };
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const cleanup = useCallback(() => {
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((t) => t.stop());
      mediaStreamRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  useEffect(() => {
    return cleanup;
  }, [cleanup]);

  const startRecording = useCallback(async () => {
    try {
      setState('connecting');
      setTranscription('');
      setResponseText('');
      setErrorMessage('');

      // Connect WebSocket
      const ws = new WebSocket(`${wsUrl}/api/voice/stream`);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'state') {
            setState(msg.state as VoiceState);
          } else if (msg.type === 'transcription') {
            setTranscription(msg.text);
            onTranscription?.(msg.text);
          } else if (msg.type === 'response') {
            setResponseText(msg.text);
            onResponse?.(msg.text);
            if (msg.audio) {
              playAudio(msg.audio);
            }
          } else if (msg.type === 'error') {
            setErrorMessage(msg.message);
            setState('error');
          }
        } catch {
          // ignore parse errors
        }
      };

      ws.onerror = () => {
        setErrorMessage('WebSocket connection failed');
        setState('error');
      };

      ws.onclose = () => {
        if (state !== 'idle') {
          setState('idle');
        }
      };

      await new Promise<void>((resolve, reject) => {
        ws.onopen = () => resolve();
        ws.onerror = () => reject(new Error('WebSocket connection failed'));
      });

      // Get microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true },
      });
      mediaStreamRef.current = stream;

      // Create audio context and processor
      const audioContext = new AudioContext({ sampleRate: 16000 });
      audioContextRef.current = audioContext;
      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e) => {
        if (ws.readyState === WebSocket.OPEN) {
          const float32 = e.inputBuffer.getChannelData(0);
          const int16 = new Int16Array(float32.length);
          for (let i = 0; i < float32.length; i++) {
            const s = Math.max(-1, Math.min(1, float32[i]));
            int16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
          }
          ws.send(int16.buffer);
        }
      };

      source.connect(processor);
      processor.connect(audioContext.destination);
      setState('recording');
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to start recording');
      setState('error');
      cleanup();
    }
  }, [wsUrl, onTranscription, onResponse, cleanup, state]);

  const stopRecording = useCallback(() => {
    // Send process command before closing
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ command: 'process' }));
      setState('processing');
      // Disconnect audio but keep WS open for response
      if (processorRef.current) {
        processorRef.current.disconnect();
        processorRef.current = null;
      }
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach((t) => t.stop());
        mediaStreamRef.current = null;
      }
    } else {
      cleanup();
      setState('idle');
    }
  }, [cleanup]);

  const stopPlayback = useCallback(() => {
    if (audioElementRef.current) {
      audioElementRef.current.pause();
      audioElementRef.current = null;
    }
    setState('idle');
  }, []);

  const playAudio = (base64Audio: string) => {
    try {
      setState('speaking');
      const byteChars = atob(base64Audio);
      const byteArray = new Uint8Array(byteChars.length);
      for (let i = 0; i < byteChars.length; i++) {
        byteArray[i] = byteChars.charCodeAt(i);
      }
      const blob = new Blob([byteArray], { type: 'audio/wav' });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audioElementRef.current = audio;
      audio.onended = () => {
        URL.revokeObjectURL(url);
        setState('idle');
        audioElementRef.current = null;
      };
      audio.play().catch(() => {
        setState('idle');
      });
    } catch {
      setState('idle');
    }
  };

  const handleMainButton = () => {
    if (state === 'recording') {
      stopRecording();
    } else if (state === 'speaking') {
      stopPlayback();
    } else if (state === 'idle' || state === 'error') {
      startRecording();
    }
  };

  const getMicButtonStyles = (): string => {
    const base =
      'relative w-14 h-14 rounded-full flex items-center justify-center transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-400 focus-visible:ring-offset-2';
    switch (state) {
      case 'recording':
        return `${base} bg-red-500 hover:bg-red-600 text-white shadow-lg shadow-red-500/30`;
      case 'processing':
        return `${base} bg-amber-500 text-white cursor-wait`;
      case 'speaking':
        return `${base} bg-teal-500 hover:bg-teal-600 text-white shadow-lg shadow-teal-500/30`;
      case 'connecting':
        return `${base} bg-gray-400 text-white cursor-wait`;
      case 'error':
        return `${base} bg-red-100 text-red-600 hover:bg-red-200 border border-red-300`;
      default:
        return `${base} bg-white text-teal-600 hover:bg-teal-50 border-2 border-teal-500 shadow-md`;
    }
  };

  const getMicIcon = () => {
    if (state === 'recording') {
      // Stop (square) icon
      return (
        <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
          <rect x="6" y="6" width="12" height="12" rx="2" />
        </svg>
      );
    }
    if (state === 'speaking') {
      // Speaker with X icon
      return (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2" />
        </svg>
      );
    }
    if (state === 'processing' || state === 'connecting') {
      // Spinner
      return (
        <svg className="w-6 h-6 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      );
    }
    // Microphone icon
    return (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M19 10v2a7 7 0 01-14 0v-2" />
        <line x1="12" y1="19" x2="12" y2="23" />
        <line x1="8" y1="23" x2="16" y2="23" />
      </svg>
    );
  };

  const getStateLabel = (): string => {
    switch (state) {
      case 'connecting':
        return 'Connecting...';
      case 'recording':
        return 'Listening...';
      case 'processing':
        return 'Processing...';
      case 'speaking':
        return 'Speaking...';
      case 'error':
        return 'Error';
      default:
        return 'Push to talk';
    }
  };

  return (
    <div className={`flex flex-col items-center gap-3 ${className}`}>
      {/* Recording pulse indicator */}
      {state === 'recording' && (
        <div className="flex items-center gap-1.5">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500" />
          </span>
          <span className="text-xs font-medium text-red-600">Recording</span>
        </div>
      )}

      {/* Main microphone button */}
      <button
        onClick={handleMainButton}
        disabled={state === 'processing' || state === 'connecting'}
        className={getMicButtonStyles()}
        aria-label={getStateLabel()}
      >
        {getMicIcon()}
      </button>

      {/* State label */}
      <span className="text-xs text-gray-500 font-medium">{getStateLabel()}</span>

      {/* Transcription display */}
      {transcription && (
        <div className="w-full max-w-xs p-2 bg-gray-50 rounded-lg border border-gray-200">
          <div className="text-[10px] uppercase tracking-wider text-gray-400 mb-1">You said</div>
          <div className="text-sm text-gray-700">{transcription}</div>
        </div>
      )}

      {/* Response display */}
      {responseText && (
        <div className="w-full max-w-xs p-2 bg-teal-50 rounded-lg border border-teal-200">
          <div className="text-[10px] uppercase tracking-wider text-teal-400 mb-1">Response</div>
          <div className="text-sm text-teal-800">{responseText}</div>
        </div>
      )}

      {/* Error display */}
      {errorMessage && state === 'error' && (
        <div className="w-full max-w-xs p-2 bg-red-50 rounded-lg border border-red-200">
          <div className="text-xs text-red-600">{errorMessage}</div>
        </div>
      )}

      {/* Component status indicators */}
      {componentStatus && (
        <div className="flex gap-2 mt-1">
          <StatusDot label="STT" active={componentStatus.stt.enabled} />
          <StatusDot label="TTS" active={componentStatus.tts.enabled} />
          <StatusDot label="Wake" active={componentStatus.wake_word.enabled} />
        </div>
      )}
    </div>
  );
};

/** Small status indicator dot with label. */
const StatusDot: React.FC<{ label: string; active: boolean }> = ({ label, active }) => (
  <div className="flex items-center gap-1" title={`${label}: ${active ? 'Active' : 'Inactive'}`}>
    <span
      className={`inline-block w-1.5 h-1.5 rounded-full ${active ? 'bg-green-500' : 'bg-gray-300'}`}
      role="status"
      aria-label={`${label} ${active ? 'active' : 'inactive'}`}
    />
    <span className="text-[10px] text-gray-400">{label}</span>
  </div>
);

export default VoiceControls;
