import { v4 as uuidv4 } from "uuid";
import { create } from "zustand";
import type {
  PostMessageStoreType,
  StoredMessage,
} from "../types/zustand/postMessage";

export const usePostMessageStore = create<PostMessageStoreType>((set, get) => ({
  // Message storage
  messages: [],

  // Add a new message to the store
  addMessage: (message: StoredMessage) => {
    set((state) => ({
      messages: [...state.messages, message],
    }));
  },

  // Get messages filtered by type
  getMessagesByType: (type: string) => {
    return get().messages.filter((msg) => msg.data.type === type);
  },

  // Get the most recent message of a specific type
  getLatestMessageByType: (type: string) => {
    const messages = get().getMessagesByType(type);
    if (messages.length === 0) return null;
    return messages.reduce((latest, current) =>
      current.receivedAt > latest.receivedAt ? current : latest,
    );
  },

  // Clear all stored messages
  clearMessages: () => {
    set(() => ({ messages: [] }));
  },

  // Remove messages older than a specified date
  removeOldMessages: (olderThan: Date) => {
    set((state) => ({
      messages: state.messages.filter((msg) => msg.receivedAt >= olderThan),
    }));
  },

  // Remove all messages of a specific type
  removeMessagesByType: (type: string) => {
    set((state) => ({
      messages: state.messages.filter((msg) => msg.data.type !== type),
    }));
  },

  // Get messages from a specific origin
  getMessagesByOrigin: (origin: string) => {
    return get().messages.filter((msg) => msg.origin === origin);
  },

  // Listener state
  isListening: false,
  setIsListening: (listening: boolean) => {
    set(() => ({ isListening: listening }));
  },

  // Allowed origins for security (empty array = allow all)
  allowedOrigins: [],
  setAllowedOrigins: (origins: string[]) => {
    set(() => ({ allowedOrigins: origins }));
  },

  // Check if an origin is allowed
  isOriginAllowed: (origin: string) => {
    const { allowedOrigins } = get();
    // If no origins specified, allow all
    if (allowedOrigins.length === 0) return true;
    // Check if origin is in allowed list
    return allowedOrigins.some((allowed) => {
      // Support wildcards like "*.example.com"
      if (allowed.includes("*")) {
        const pattern = allowed.replace(/\*/g, ".*");
        return new RegExp(`^${pattern}$`).test(origin);
      }
      return allowed === origin;
    });
  },
}));
