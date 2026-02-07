"use client";

import {
  ArchiveIcon,
  MessageSquareIcon,
  MoreVerticalIcon,
  PlusIcon,
  RotateCcwIcon,
  TrashIcon,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import {
  type ChatThread,
  createThread,
  deleteThread,
  listThreads,
  updateThread,
} from "@/services/chatService";
import useChatStore from "@/stores/chatStore";

interface ThreadListState {
  threads: ChatThread[];
  archivedThreads: ChatThread[];
  isLoading: boolean;
  error: string | null;
}

interface ThreadListProps {
  currentThreadId?: number;
  spaceId: number;
  className?: string;
  onThreadCreated?: (threadId: number) => void;
}

export function ThreadList({
  currentThreadId,
  spaceId,
  className,
  onThreadCreated,
}: ThreadListProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { spaceId: urlSpaceId } = useParams<{ spaceId: string }>();
  const setCurrentChatId = useChatStore((state) => state.setCurrentChatId);

  const [state, setState] = useState<ThreadListState>({
    threads: [],
    archivedThreads: [],
    isLoading: false,
    error: null,
  });
  const [showArchived, setShowArchived] = useState(false);

  // Load threads from API
  const loadThreads = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      const response = await listThreads(spaceId);
      setState({
        threads: response.threads,
        archivedThreads: response.archived_threads,
        isLoading: false,
        error: null,
      });
    } catch (error) {
      console.error("[ThreadList] Failed to load threads:", error);
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: t("spaces.chats.threadList.failedToLoad"),
      }));
    }
  }, [spaceId]);

  useEffect(() => {
    loadThreads();
  }, [loadThreads]);

  // Handle new thread creation
  const handleNewThread = async () => {
    try {
      const newThread = await createThread(spaceId, t("spaces.chats.newChat"));
      setCurrentChatId(newThread.id.toString());

      // Reload threads to update the list
      await loadThreads();

      // Navigate to the new thread
      navigate(`/spaces/${urlSpaceId}/chats`);

      // Notify parent component
      onThreadCreated?.(newThread.id);

      toast.success(t("spaces.chats.chatCreated"));
    } catch (error) {
      console.error("[ThreadList] Failed to create thread:", error);
      toast.error(t("spaces.chats.threadList.failedToCreateChat"));
    }
  };

  // Handle thread archive
  const handleArchive = async (threadId: number) => {
    try {
      await updateThread(threadId, { archived: true });
      await loadThreads();
      toast.success(t("spaces.chats.threadList.archived"));
    } catch (error) {
      console.error("[ThreadList] Failed to archive thread:", error);
      toast.error(t("spaces.chats.threadList.failedToArchive"));
    }
  };

  // Handle thread unarchive
  const handleUnarchive = async (threadId: number) => {
    try {
      await updateThread(threadId, { archived: false });
      await loadThreads();
      toast.success(t("spaces.chats.threadList.restored"));
    } catch (error) {
      console.error("[ThreadList] Failed to unarchive thread:", error);
      toast.error(t("spaces.chats.threadList.failedToRestore"));
    }
  };

  // Handle thread delete
  const handleDelete = async (threadId: number) => {
    if (!confirm(t("spaces.chats.threadList.confirmDelete"))) {
      return;
    }

    try {
      await deleteThread(threadId);
      await loadThreads();

      // If current thread is deleted, clear it
      if (threadId === currentThreadId) {
        setCurrentChatId(null);
      }

      toast.success(t("spaces.chats.threadList.deleted"));
    } catch (error) {
      console.error("[ThreadList] Failed to delete thread:", error);
      toast.error(t("spaces.chats.threadList.failedToDelete"));
    }
  };

  // Handle thread switch
  const handleSwitchToThread = (threadId: number) => {
    setCurrentChatId(threadId.toString());
    navigate(`/spaces/${urlSpaceId}/chats`);
  };

  const displayedThreads = showArchived ? state.archivedThreads : state.threads;

  if (state.isLoading) {
    return (
      <div className={cn("flex h-full flex-col", className)}>
        <div className="flex items-center justify-center p-4">
          <span className="text-muted-foreground text-sm">
            {t("spaces.chats.threadList.loading")}
          </span>
        </div>
      </div>
    );
  }

  if (state.error) {
    return (
      <div className={cn("flex h-full flex-col", className)}>
        <div className="p-4 text-center">
          <span className="text-destructive text-sm">{state.error}</span>
          <Button
            variant="ghost"
            size="sm"
            className="mt-2"
            onClick={loadThreads}
          >
            {t("spaces.chats.threadList.retry")}
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("flex h-full flex-col", className)}>
      {/* Header with New Chat button */}
      <div className="flex items-center justify-between border-b p-3">
        <h2 className="font-semibold text-sm">
          {t("spaces.chats.threadList.conversations")}
        </h2>
        <Button
          variant="ghost"
          size="icon"
          className="size-8"
          onClick={handleNewThread}
          title={t("spaces.chats.newChat")}
        >
          <PlusIcon className="size-4" />
        </Button>
      </div>

      {/* Tab toggle for active/archived */}
      <div className="flex border-b">
        <button
          type="button"
          onClick={() => setShowArchived(false)}
          className={cn(
            "flex-1 px-3 py-2 text-center text-xs font-medium transition-colors",
            !showArchived
              ? "border-b-2 border-primary text-primary"
              : "text-muted-foreground hover:text-foreground",
          )}
        >
          {t("spaces.chats.threadList.active")} ({state.threads.length})
        </button>
        <button
          type="button"
          onClick={() => setShowArchived(true)}
          className={cn(
            "flex-1 px-3 py-2 text-center text-xs font-medium transition-colors",
            showArchived
              ? "border-b-2 border-primary text-primary"
              : "text-muted-foreground hover:text-foreground",
          )}
        >
          {t("spaces.chats.threadList.archivedTab")} (
          {state.archivedThreads.length})
        </button>
      </div>

      {/* Thread list */}
      <div className="flex-1 overflow-y-auto">
        {displayedThreads.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-6 text-center">
            <MessageSquareIcon className="mb-2 size-8 text-muted-foreground/50" />
            <p className="text-muted-foreground text-sm">
              {showArchived
                ? t("spaces.chats.threadList.noArchivedConversations")
                : t("spaces.chats.threadList.noConversations")}
            </p>
            {!showArchived && (
              <Button
                variant="outline"
                size="sm"
                className="mt-3"
                onClick={handleNewThread}
              >
                <PlusIcon className="mr-1 size-3" />
                {t("spaces.chats.threadList.startConversation")}
              </Button>
            )}
          </div>
        ) : (
          <div className="space-y-1 p-2">
            {displayedThreads.map((thread) => (
              <ThreadListItemComponent
                key={thread.id}
                thread={thread}
                isActive={thread.id === currentThreadId}
                isArchived={showArchived}
                onClick={() => handleSwitchToThread(thread.id)}
                onArchive={() => handleArchive(thread.id)}
                onUnarchive={() => handleUnarchive(thread.id)}
                onDelete={() => handleDelete(thread.id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

interface ThreadListItemComponentProps {
  thread: ChatThread;
  isActive: boolean;
  isArchived: boolean;
  onClick: () => void;
  onArchive: () => void;
  onUnarchive: () => void;
  onDelete: () => void;
}

function ThreadListItemComponent({
  thread,
  isActive,
  isArchived,
  onClick,
  onArchive,
  onUnarchive,
  onDelete,
}: ThreadListItemComponentProps) {
  const { t } = useTranslation();

  return (
    <div
      className={cn(
        "group flex items-center gap-2 rounded-lg px-3 py-2 transition-colors cursor-pointer",
        isActive ? "bg-accent text-accent-foreground" : "hover:bg-muted/50",
      )}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") onClick();
      }}
      role="button"
      tabIndex={0}
    >
      <MessageSquareIcon className="size-4 shrink-0 text-muted-foreground" />
      <div className="flex-1 min-w-0">
        <p className="truncate text-sm font-medium">
          {thread.title || t("spaces.chats.newChat")}
        </p>
        <p className="truncate text-xs text-muted-foreground">
          {formatRelativeTime(
            new Date(thread.updated_at || thread.created_at),
            t,
          )}
        </p>
      </div>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="size-7 opacity-0 group-hover:opacity-100 transition-opacity"
            onClick={(e) => e.stopPropagation()}
          >
            <MoreVerticalIcon className="size-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          {isArchived ? (
            <DropdownMenuItem onClick={onUnarchive}>
              <RotateCcwIcon className="mr-2 size-4" />
              {t("spaces.chats.threadList.unarchive")}
            </DropdownMenuItem>
          ) : (
            <DropdownMenuItem onClick={onArchive}>
              <ArchiveIcon className="mr-2 size-4" />
              {t("spaces.chats.threadList.archive")}
            </DropdownMenuItem>
          )}
          <DropdownMenuSeparator />
          <DropdownMenuItem
            onClick={onDelete}
            className="text-destructive focus:text-destructive"
          >
            <TrashIcon className="mr-2 size-4" />
            {t("spaces.chats.threadList.delete")}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}

/**
 * Format a date as relative time (e.g., "2 hours ago", "Yesterday")
 */
function formatRelativeTime(
  date: Date,
  t: (key: string, options?: any) => string,
): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSecs < 60) return t("spaces.chats.threadList.time.justNow");
  if (diffMins < 60)
    return t("spaces.chats.threadList.time.minsAgo", { count: diffMins });
  if (diffHours < 24)
    return t("spaces.chats.threadList.time.hoursAgo", { count: diffHours });
  if (diffDays === 1) return t("spaces.chats.threadList.time.yesterday");
  if (diffDays < 7)
    return t("spaces.chats.threadList.time.daysAgo", { count: diffDays });

  return date.toLocaleDateString();
}
