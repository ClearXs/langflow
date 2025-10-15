// Types for postMessage communication with external systems

export interface PostMessageData<T = any> {
  type: string;
  payload?: T;
  timestamp: number;
  source?: string;
}

export interface StoredMessage<T = any> {
  id: string;
  data: PostMessageData<T>;
  origin: string;
  receivedAt: Date;
}

export interface PostMessageStoreType {
  // Stored messages
  messages: StoredMessage[];

  // Add a new message
  addMessage: (message: StoredMessage) => void;

  // Get messages by type
  getMessagesByType: (type: string) => StoredMessage[];

  // Get the latest message by type
  getLatestMessageByType: (type: string) => StoredMessage | null;

  // Clear all messages
  clearMessages: () => void;

  // Remove messages older than a certain time
  removeOldMessages: (olderThan: Date) => void;

  // Remove messages by type
  removeMessagesByType: (type: string) => void;

  // Get all messages from a specific origin
  getMessagesByOrigin: (origin: string) => StoredMessage[];

  // Listener state
  isListening: boolean;
  setIsListening: (listening: boolean) => void;

  // Allowed origins for security
  allowedOrigins: string[];
  setAllowedOrigins: (origins: string[]) => void;

  // Check if origin is allowed
  isOriginAllowed: (origin: string) => boolean;
}
