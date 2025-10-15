import { useEffect, useCallback, useRef } from "react";
import { v4 as uuidv4 } from "uuid";
import { usePostMessageStore } from "@/stores/postMessageStore";
import type { PostMessageData, StoredMessage } from "@/types/zustand/postMessage";

export interface UsePostMessageOptions {
  // Origins to accept messages from (empty = all origins)
  allowedOrigins?: string[];

  // Callback when a message is received
  onMessage?: (message: StoredMessage) => void;

  // Filter messages by type
  messageTypes?: string[];

  // Auto-cleanup old messages
  autoCleanup?: boolean;

  // Cleanup interval in milliseconds (default: 5 minutes)
  cleanupInterval?: number;

  // Max age for messages in milliseconds (default: 1 hour)
  maxMessageAge?: number;

  // Enable/disable listening
  enabled?: boolean;
}

export interface UsePostMessageReturn {
  // Send a message to parent window
  sendToParent: <T = any>(type: string, payload?: T, targetOrigin?: string) => void;

  // Send a message to a specific window
  sendToWindow: <T = any>(
    targetWindow: Window,
    type: string,
    payload?: T,
    targetOrigin?: string,
  ) => void;

  // Get all stored messages
  messages: StoredMessage[];

  // Get messages by type
  getMessagesByType: (type: string) => StoredMessage[];

  // Get latest message by type
  getLatestMessage: (type: string) => StoredMessage | null;

  // Clear all messages
  clearMessages: () => void;

  // Check if currently listening
  isListening: boolean;
}

export function usePostMessage(
  options: UsePostMessageOptions = {},
): UsePostMessageReturn {
  const {
    allowedOrigins = [],
    onMessage,
    messageTypes,
    autoCleanup = true,
    cleanupInterval = 5 * 60 * 1000, // 5 minutes
    maxMessageAge = 60 * 60 * 1000, // 1 hour
    enabled = true,
  } = options;

  const {
    messages,
    addMessage,
    getMessagesByType,
    getLatestMessageByType,
    clearMessages,
    removeOldMessages,
    setAllowedOrigins,
    isOriginAllowed,
    isListening,
    setIsListening,
  } = usePostMessageStore();

  const cleanupIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Set allowed origins on mount or when they change
  useEffect(() => {
    if (allowedOrigins.length > 0) {
      setAllowedOrigins(allowedOrigins);
    }
  }, [allowedOrigins, setAllowedOrigins]);

  // Handle incoming messages
  const handleMessage = useCallback(
    (event: MessageEvent) => {
      // Security check: validate origin
      if (!isOriginAllowed(event.origin)) {
        console.warn(`Message from unauthorized origin blocked: ${event.origin}`);
        return;
      }

      // Parse message data
      let messageData: PostMessageData;
      try {
        // Handle both string and object messages
        if (typeof event.data === "string") {
          messageData = JSON.parse(event.data);
        } else {
          messageData = event.data;
        }
      } catch (error) {
        console.warn("Failed to parse postMessage data:", error);
        return;
      }

      // Filter by message type if specified
      if (messageTypes && messageTypes.length > 0) {
        if (!messageTypes.includes(messageData.type)) {
          return;
        }
      }

      // Create stored message
      const storedMessage: StoredMessage = {
        id: uuidv4(),
        data: messageData,
        origin: event.origin,
        receivedAt: new Date(),
      };

      // Add to store
      addMessage(storedMessage);

      // Call custom callback if provided
      if (onMessage) {
        onMessage(storedMessage);
      }
    },
    [isOriginAllowed, messageTypes, addMessage, onMessage],
  );

  // Set up message listener
  useEffect(() => {
    if (!enabled) {
      setIsListening(false);
      return;
    }

    window.addEventListener("message", handleMessage);
    setIsListening(true);

    return () => {
      window.removeEventListener("message", handleMessage);
      setIsListening(false);
    };
  }, [enabled, handleMessage, setIsListening]);

  // Auto-cleanup old messages
  useEffect(() => {
    if (!autoCleanup || !enabled) return;

    cleanupIntervalRef.current = setInterval(() => {
      const cutoffTime = new Date(Date.now() - maxMessageAge);
      removeOldMessages(cutoffTime);
    }, cleanupInterval);

    return () => {
      if (cleanupIntervalRef.current) {
        clearInterval(cleanupIntervalRef.current);
      }
    };
  }, [autoCleanup, cleanupInterval, maxMessageAge, removeOldMessages, enabled]);

  // Send message to parent window
  const sendToParent = useCallback(
    <T = any>(type: string, payload?: T, targetOrigin: string = "*") => {
      if (!window.parent) {
        console.warn("No parent window available");
        return;
      }

      const message: PostMessageData<T> = {
        type,
        payload,
        timestamp: Date.now(),
        source: "langflow",
      };

      window.parent.postMessage(message, targetOrigin);
    },
    [],
  );

  // Send message to a specific window
  const sendToWindow = useCallback(
    <T = any>(
      targetWindow: Window,
      type: string,
      payload?: T,
      targetOrigin: string = "*",
    ) => {
      const message: PostMessageData<T> = {
        type,
        payload,
        timestamp: Date.now(),
        source: "langflow",
      };

      targetWindow.postMessage(message, targetOrigin);
    },
    [],
  );

  return {
    sendToParent,
    sendToWindow,
    messages,
    getMessagesByType,
    getLatestMessage: getLatestMessageByType,
    clearMessages,
    isListening,
  };
}
