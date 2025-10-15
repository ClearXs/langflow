/**
 * PostMessage Context Provider
 *
 * Provides postMessage communication capabilities throughout the app.
 * This context wraps the usePostMessage hook and makes it accessible
 * to all components via usePostMessageContext.
 */

import React, { createContext, useContext, ReactNode, useCallback } from "react";
import { usePostMessage, UsePostMessageOptions } from "@/customization/hooks/use-post-message";
import type { StoredMessage } from "@/types/zustand/postMessage";

// Context value type
export interface PostMessageContextValue {
  // Send message to parent window
  sendToParent: <T = any>(type: string, payload?: T, targetOrigin?: string) => void;

  // Send message to specific window
  sendToWindow: <T = any>(
    targetWindow: Window,
    type: string,
    payload?: T,
    targetOrigin?: string,
  ) => void;

  // All stored messages
  messages: StoredMessage[];

  // Get messages by type
  getMessagesByType: (type: string) => StoredMessage[];

  // Get latest message by type
  getLatestMessage: (type: string) => StoredMessage | null;

  // Clear all messages
  clearMessages: () => void;

  // Is currently listening
  isListening: boolean;
}

// Create context
const PostMessageContext = createContext<PostMessageContextValue | null>(null);

// Provider props
export interface PostMessageProviderProps {
  children: ReactNode;

  // Hook options
  options?: UsePostMessageOptions;

  // Global message handler (optional)
  onGlobalMessage?: (message: StoredMessage) => void;
}

/**
 * PostMessage Provider Component
 *
 * Wraps the application and provides postMessage communication capabilities.
 */
export const PostMessageProvider: React.FC<PostMessageProviderProps> = ({
  children,
  options = {},
  onGlobalMessage,
}) => {
  // Merge global handler with options handler
  const handleMessage = useCallback(
    (message: StoredMessage) => {
      // Call options handler if provided
      if (options.onMessage) {
        options.onMessage(message);
      }

      // Call global handler if provided
      if (onGlobalMessage) {
        onGlobalMessage(message);
      }
    },
    [options.onMessage, onGlobalMessage],
  );

  // Initialize the hook with merged options
  const postMessageHook = usePostMessage({
    ...options,
    onMessage: handleMessage,
  });

  return (
    <PostMessageContext.Provider value={postMessageHook}>
      {children}
    </PostMessageContext.Provider>
  );
};

/**
 * Hook to consume PostMessage context
 *
 * @throws Error if used outside of PostMessageProvider
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { sendToParent, messages } = usePostMessageContext();
 *
 *   const handleClick = () => {
 *     sendToParent("USER_CLICKED", { buttonId: "submit" });
 *   };
 *
 *   return <button onClick={handleClick}>Send Message</button>;
 * }
 * ```
 */
export const usePostMessageContext = (): PostMessageContextValue => {
  const context = useContext(PostMessageContext);

  if (!context) {
    throw new Error(
      "usePostMessageContext must be used within a PostMessageProvider. " +
      "Make sure your component is wrapped with <PostMessageProvider>."
    );
  }

  return context;
};

// Export context for advanced usage
export { PostMessageContext };

// Default export
export default PostMessageProvider;
