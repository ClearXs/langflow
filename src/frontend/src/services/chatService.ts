import { api } from "@/controllers/API/api";

export interface ChatThread {
  id: number;
  space_id: number;
  title: string;
  archived: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface ChatMessage {
  id: number;
  thread_id: number;
  role: "user" | "assistant" | "system";
  content: unknown;
  created_at: string;
}

export interface ThreadListResponse {
  threads: ChatThread[];
  archived_threads: ChatThread[];
}

export interface ThreadHistoryResponse {
  messages: ChatMessage[];
}

export interface CreateThreadRequest {
  space_id: number;
  title?: string;
}

export interface AppendMessageRequest {
  role: "user" | "assistant";
  content: unknown;
}

export interface NewChatRequest {
  chat_id: number;
  user_query: string;
  space_id: number;
  messages?: Array<{ role: string; content: string }>;
  attachments?: Array<Record<string, unknown>>;
  mentioned_document_ids?: number[];
}

/**
 * List all threads for a space
 */
export async function listThreads(
  spaceId: number,
): Promise<ThreadListResponse> {
  const response = await api.get<ThreadListResponse>(
    `/api/v1/chats/threads?space_id=${spaceId}`,
  );
  return response.data;
}

/**
 * Create a new thread
 */
export async function createThread(
  spaceId: number,
  title = "New Chat",
): Promise<ChatThread> {
  const response = await api.post<ChatThread>("/api/v1/chats/threads", {
    space_id: spaceId,
    title,
  });
  return response.data;
}

/**
 * Load thread history
 */
export async function getThreadMessages(
  threadId: number,
): Promise<ThreadHistoryResponse> {
  const response = await api.get<ThreadHistoryResponse>(
    `/api/v1/chats/threads/${threadId}`,
  );
  return response.data;
}

/**
 * Append a message to a thread
 */
export async function appendMessage(
  threadId: number,
  message: AppendMessageRequest,
): Promise<ChatMessage> {
  const response = await api.post<ChatMessage>(
    `/api/v1/chats/threads/${threadId}/messages`,
    message,
  );
  return response.data;
}

/**
 * Update thread (rename or archive)
 */
export async function updateThread(
  threadId: number,
  updates: { title?: string; archived?: boolean },
): Promise<ChatThread> {
  const response = await api.put<ChatThread>(
    `/api/v1/chats/threads/${threadId}`,
    updates,
  );
  return response.data;
}

/**
 * Delete a thread
 */
export async function deleteThread(threadId: number): Promise<void> {
  await api.delete(`/api/v1/chats/threads/${threadId}`);
}
