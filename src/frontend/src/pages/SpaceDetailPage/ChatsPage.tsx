"use client";

import {
  type AppendMessage,
  AssistantRuntimeProvider,
  type ThreadMessageLike,
  useExternalStoreRuntime,
} from "@assistant-ui/react";
import { MessageSquare, Plus } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { Thread } from "@/components/assistant-ui/thread";
import { ThreadList } from "@/components/assistant-ui/thread-list";
import { Button } from "@/components/ui/button";
import {
  appendMessage,
  type ChatMessage,
  createThread,
  getThreadMessages,
} from "@/services/chatService";
import useChatStore from "@/stores/chatStore";
import useSpacesStore from "@/stores/spacesStore";

/**
 * Extract thinking steps from message content
 */
function extractThinkingSteps(content: unknown): unknown[] {
  if (!Array.isArray(content)) return [];

  const thinkingPart = content.find(
    (part: unknown) =>
      typeof part === "object" &&
      part !== null &&
      "type" in part &&
      (part as { type: string }).type === "thinking-steps",
  ) as { type: "thinking-steps"; steps: unknown[] } | undefined;

  return thinkingPart?.steps || [];
}

/**
 * Convert backend message to assistant-ui ThreadMessageLike format
 * Filters out 'thinking-steps' part as it's handled separately
 */
function convertToThreadMessage(msg: ChatMessage): ThreadMessageLike {
  let content: ThreadMessageLike["content"];

  if (typeof msg.content === "string") {
    content = [{ type: "text", text: msg.content }];
  } else if (Array.isArray(msg.content)) {
    // Filter out custom metadata parts - they're handled separately
    const filteredContent = msg.content.filter((part: unknown) => {
      if (typeof part !== "object" || part === null || !("type" in part))
        return true;
      const partType = (part as { type: string }).type;
      // Filter out thinking-steps and mentioned-documents
      return (
        partType !== "thinking-steps" && partType !== "mentioned-documents"
      );
    });
    content =
      filteredContent.length > 0
        ? (filteredContent as ThreadMessageLike["content"])
        : [{ type: "text", text: "" }];
  } else {
    content = [{ type: "text", text: String(msg.content) }];
  }

  return {
    id: `msg-${msg.id}`,
    role: msg.role,
    content,
    createdAt: new Date(msg.created_at),
  };
}

export default function ChatsPage() {
  const { t } = useTranslation();
  const { spaceId } = useParams<{ spaceId: string }>();
  const navigate = useNavigate();
  const [isInitializing, setIsInitializing] = useState(true);
  const [threadId, setThreadId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ThreadMessageLike[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [messageThinkingSteps, setMessageThinkingSteps] = useState<
    Map<string, any[]>
  >(new Map());
  const [mentionedDocuments, setMentionedDocuments] = useState<any[]>([]);
  const abortControllerRef = useRef<AbortController | null>(null);

  const currentChatId = useChatStore((state) => state.currentChatId);
  const setCurrentChatId = useChatStore((state) => state.setCurrentChatId);
  const activeSpace = useSpacesStore((state) => state.getActiveSpace());

  const spaceIdNum = useMemo(() => {
    const parsed = spaceId ? parseInt(spaceId, 10) : 0;
    return isNaN(parsed) ? 0 : parsed;
  }, [spaceId]);

  // Initialize thread
  const initializeThread = useCallback(async () => {
    if (!spaceIdNum) return;

    setIsInitializing(true);

    try {
      if (currentChatId) {
        // Load existing thread
        const chatIdNum = parseInt(currentChatId, 10);
        if (!isNaN(chatIdNum)) {
          setThreadId(chatIdNum);
          const response = await getThreadMessages(chatIdNum);
          if (response.messages && response.messages.length > 0) {
            const loadedMessages = response.messages.map(
              convertToThreadMessage,
            );
            setMessages(loadedMessages);
          }
        }
      }
    } catch (error) {
      console.error("[ChatsPage] Failed to initialize thread:", error);
      toast.error(t("spaces.chats.failedToLoad"));
    } finally {
      setIsInitializing(false);
    }
  }, [currentChatId, spaceIdNum]);

  useEffect(() => {
    initializeThread();
  }, [initializeThread]);

  // Create new chat
  const handleNewChat = useCallback(async () => {
    if (!spaceIdNum) return;

    try {
      const newThread = await createThread(spaceIdNum, "New Chat");
      setThreadId(newThread.id);
      setCurrentChatId(newThread.id.toString());
      setMessages([]);
      toast.success(t("spaces.chats.chatCreated"));
    } catch (error) {
      console.error("[ChatsPage] Failed to create thread:", error);
      toast.error(t("spaces.chats.failedToCreate"));
    }
  }, [spaceIdNum, setCurrentChatId, t]);

  // Cancel ongoing request
  const cancelRun = useCallback(async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsRunning(false);
  }, []);

  // Handle new message from user
  const onNew = useCallback(
    async (message: AppendMessage) => {
      if (!threadId) return;

      // Extract user query text from content parts
      let userQuery = "";
      for (const part of message.content) {
        if (part.type === "text") {
          userQuery += part.text;
        }
      }

      if (!userQuery.trim()) return;

      // Add user message to state
      const userMsgId = `msg-user-${Date.now()}`;
      const userMessage: ThreadMessageLike = {
        id: userMsgId,
        role: "user",
        content: message.content,
        createdAt: new Date(),
      };
      setMessages((prev) => [...prev, userMessage]);

      // Persist user message
      appendMessage(threadId, {
        role: "user",
        content: message.content,
      }).catch((err) => console.error("Failed to persist user message:", err));

      // Start streaming response
      setIsRunning(true);
      const controller = new AbortController();
      abortControllerRef.current = controller;

      // Prepare assistant message
      const assistantMsgId = `msg-assistant-${Date.now()}`;
      let assistantContent = "";
      const currentThinkingSteps: any[] = [];

      // Add placeholder assistant message
      setMessages((prev) => [
        ...prev,
        {
          id: assistantMsgId,
          role: "assistant",
          content: [{ type: "text", text: "" }],
          createdAt: new Date(),
        },
      ]);

      try {
        const backendUrl = window.location.origin;

        // Build message history for context
        const messageHistory = messages
          .filter((m) => m.role === "user" || m.role === "assistant")
          .map((m) => {
            let text = "";
            for (const part of m.content) {
              if (
                typeof part === "object" &&
                part.type === "text" &&
                "text" in part
              ) {
                text += part.text;
              }
            }
            return { role: m.role, content: text };
          })
          .filter((m) => m.content.length > 0);

        const response = await fetch(`${backendUrl}/api/v1/chats/new_chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            chat_id: threadId,
            user_query: userQuery.trim(),
            space_id: spaceIdNum,
            messages: messageHistory,
            mentioned_document_ids:
              mentionedDocuments.length > 0
                ? mentionedDocuments.map((d) => d.id)
                : undefined,
          }),
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`Backend error: ${response.status}`);
        }

        if (!response.body) {
          throw new Error("No response body");
        }

        // Parse SSE stream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // Process complete SSE events
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";

            for (const line of lines) {
              if (line.startsWith("data: ")) {
                const data = line.slice(6);
                if (data === "[DONE]") {
                  break;
                }

                try {
                  const event = JSON.parse(data);

                  if (event.type === "text-delta") {
                    assistantContent += event.delta;
                    setMessages((prev) => {
                      const newMessages = [...prev];
                      const lastMsg = newMessages[newMessages.length - 1];
                      if (lastMsg && lastMsg.id === assistantMsgId) {
                        lastMsg.content = [
                          { type: "text", text: assistantContent },
                        ];
                      }
                      return newMessages;
                    });
                  } else if (event.type === "thinking-step") {
                    // Handle thinking step event
                    const stepData = event.data;
                    const existingStepIndex = currentThinkingSteps.findIndex(
                      (s) => s.id === stepData.id,
                    );

                    if (existingStepIndex >= 0) {
                      // Update existing step
                      currentThinkingSteps[existingStepIndex] = stepData;
                    } else {
                      // Add new step
                      currentThinkingSteps.push(stepData);
                    }

                    // Update thinking steps map
                    setMessageThinkingSteps((prev) => {
                      const next = new Map(prev);
                      next.set(assistantMsgId, [...currentThinkingSteps]);
                      return next;
                    });
                  }
                } catch (e) {
                  console.error("Failed to parse SSE event:", e);
                }
              }
            }
          }

          // Persist assistant message
          if (assistantContent.trim()) {
            appendMessage(threadId, {
              role: "assistant",
              content: [{ type: "text", text: assistantContent }],
            }).catch((err) =>
              console.error("Failed to persist assistant message:", err),
            );
          }
        } finally {
          await reader.cancel();
          // Clear mentioned documents after streaming completes
          setMentionedDocuments([]);
        }
      } catch (error: unknown) {
        if (error instanceof Error && error.name === "AbortError") {
          console.log("[ChatsPage] Request aborted by user");
        } else {
          console.error("[ChatsPage] Streaming error:", error);
          toast.error(t("spaces.chats.failedToGetResponse"));
        }
      } finally {
        setIsRunning(false);
        abortControllerRef.current = null;
      }
    },
    [threadId, spaceIdNum, messages],
  );

  // Configure assistant-ui runtime
  const runtime = useExternalStoreRuntime({
    messages,
    isRunning,
    onNew,
    onCancel: cancelRun,
    convertMessage: (msg) => msg,
  });

  const hasActiveChat = threadId !== null && !isInitializing;

  // Handle thread created from sidebar
  const handleThreadCreated = useCallback((newThreadId: number) => {
    setThreadId(newThreadId);
    setMessages([]);
  }, []);

  return (
    <div className="flex h-full">
      {/* Thread List Sidebar */}
      <div className="w-80 border-r flex-shrink-0">
        <ThreadList
          currentThreadId={threadId || undefined}
          spaceId={spaceIdNum}
          onThreadCreated={handleThreadCreated}
        />
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {!hasActiveChat ? (
          <div className="h-full flex flex-col items-center justify-center py-20 px-8">
            <div className="rounded-full bg-muted p-6 mb-6">
              <MessageSquare className="h-12 w-12 text-muted-foreground" />
            </div>
            <h3 className="text-xl font-semibold mb-3">
              {t("spaces.chats.startConversation")}
            </h3>
            <p className="text-muted-foreground text-center max-w-md mb-8 text-base">
              {t("spaces.chats.startConversationDesc")}
            </p>
            <Button onClick={handleNewChat} size="lg">
              <Plus className="mr-2 h-5 w-5" />
              {t("spaces.chats.newChat")}
            </Button>
          </div>
        ) : (
          <AssistantRuntimeProvider runtime={runtime}>
            <div className="h-full">
              <Thread
                messageThinkingSteps={messageThinkingSteps}
                mentionedDocuments={mentionedDocuments}
                onMentionedDocumentsChange={setMentionedDocuments}
                spaceId={spaceIdNum}
              />
            </div>
          </AssistantRuntimeProvider>
        )}
      </div>
    </div>
  );
}
