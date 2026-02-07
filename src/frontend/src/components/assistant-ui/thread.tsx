import {
  ActionBarPrimitive,
  AssistantIf,
  BranchPickerPrimitive,
  ComposerPrimitive,
  ErrorPrimitive,
  MessagePrimitive,
  ThreadPrimitive,
  useAssistantState,
  useMessage,
  useThreadViewport,
} from "@assistant-ui/react";
import {
  AlertCircle,
  ArrowDownIcon,
  ArrowUpIcon,
  Brain,
  CheckCircle2,
  CheckIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  CopyIcon,
  DownloadIcon,
  FileText,
  Loader2,
  PencilIcon,
  Plug2,
  Plus,
  RefreshCwIcon,
  Search,
  Sparkles,
  SquareIcon,
  X,
} from "lucide-react";
import {
  createContext,
  type FC,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { createPortal } from "react-dom";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import {
  ComposerAddAttachment,
  ComposerAttachments,
  UserMessageAttachments,
} from "@/components/assistant-ui/attachment";
import { MarkdownText } from "@/components/assistant-ui/markdown-text";
import { ToolFallback } from "@/components/assistant-ui/tool-fallback";
import { TooltipIconButton } from "@/components/assistant-ui/tooltip-icon-button";
import {
  DocumentMentionBadge,
  DocumentMentionPopover,
} from "@/components/chat/document-mention";
import {
  ChainOfThought,
  ChainOfThoughtContent,
  ChainOfThoughtItem,
  ChainOfThoughtStep,
  ChainOfThoughtTrigger,
} from "@/components/prompt-kit/chain-of-thought";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";

// TODO: Define ThinkingStep type or import from appropriate location
export interface ThinkingStep {
  id: string;
  title: string;
  status: "pending" | "in_progress" | "completed";
  items?: string[];
}

/**
 * Props for the Thread component
 */
interface ThreadProps {
  messageThinkingSteps?: Map<string, ThinkingStep[]>;
  /** Optional header component to render at the top of the viewport (sticky) */
  header?: React.ReactNode;
  /** Document mention functionality */
  mentionedDocuments?: any[];
  onMentionedDocumentsChange?: (documents: any[]) => void;
  spaceId?: number;
}

// Context to pass thinking steps to AssistantMessage
const ThinkingStepsContext = createContext<Map<string, ThinkingStep[]>>(
  new Map(),
);

// Context to pass document mention functionality to Composer
interface DocumentMentionContextValue {
  mentionedDocuments: any[];
  onMentionedDocumentsChange: (documents: any[]) => void;
  spaceId?: number;
}

const DocumentMentionContext = createContext<
  DocumentMentionContextValue | undefined
>(undefined);

/**
 * Get icon based on step status and title
 */
function getStepIcon(
  status: "pending" | "in_progress" | "completed",
  title: string,
) {
  const titleLower = title.toLowerCase();

  if (status === "in_progress") {
    return <Loader2 className="size-4 animate-spin text-primary" />;
  }

  if (status === "completed") {
    return <CheckCircle2 className="size-4 text-emerald-500" />;
  }

  if (titleLower.includes("search") || titleLower.includes("knowledge")) {
    return <Search className="size-4 text-muted-foreground" />;
  }

  if (titleLower.includes("analy") || titleLower.includes("understand")) {
    return <Brain className="size-4 text-muted-foreground" />;
  }

  return <Sparkles className="size-4 text-muted-foreground" />;
}

/**
 * Chain of thought display component with smart expand/collapse behavior
 */
const ThinkingStepsDisplay: FC<{
  steps: ThinkingStep[];
  isThreadRunning?: boolean;
}> = ({ steps, isThreadRunning = true }) => {
  // Track which steps the user has manually toggled (overrides auto behavior)
  const [manualOverrides, setManualOverrides] = useState<
    Record<string, boolean>
  >({});
  // Track previous step statuses to detect changes
  const prevStatusesRef = useRef<Record<string, string>>({});

  // Derive effective status: if thread stopped and step is in_progress, treat as completed
  const getEffectiveStatus = (
    step: ThinkingStep,
  ): "pending" | "in_progress" | "completed" => {
    if (step.status === "in_progress" && !isThreadRunning) {
      return "completed"; // Thread was stopped, so mark as completed
    }
    return step.status;
  };

  // Check if any step is effectively in progress
  const hasInProgressStep = steps.some(
    (step) => getEffectiveStatus(step) === "in_progress",
  );

  // Find the last completed step index (using effective status)
  const lastCompletedIndex = steps
    .map((s, i) => (getEffectiveStatus(s) === "completed" ? i : -1))
    .filter((i) => i !== -1)
    .pop();

  // Clear manual overrides when a step's status changes
  useEffect(() => {
    const currentStatuses: Record<string, string> = {};
    steps.forEach((step) => {
      currentStatuses[step.id] = step.status;
      // If status changed, clear any manual override for this step
      if (
        prevStatusesRef.current[step.id] &&
        prevStatusesRef.current[step.id] !== step.status
      ) {
        setManualOverrides((prev) => {
          const next = { ...prev };
          delete next[step.id];
          return next;
        });
      }
    });
    prevStatusesRef.current = currentStatuses;
  }, [steps]);

  if (steps.length === 0) return null;

  const getStepOpenState = (step: ThinkingStep, index: number): boolean => {
    const effectiveStatus = getEffectiveStatus(step);
    // If user has manually toggled, respect that
    if (manualOverrides[step.id] !== undefined) {
      return manualOverrides[step.id];
    }
    // Auto behavior: open if in progress
    if (effectiveStatus === "in_progress") {
      return true;
    }
    // Auto behavior: keep last completed step open if no in-progress step
    if (!hasInProgressStep && index === lastCompletedIndex) {
      return true;
    }
    // Default: collapsed
    return false;
  };

  const handleToggle = (stepId: string, currentOpen: boolean) => {
    setManualOverrides((prev) => ({
      ...prev,
      [stepId]: !currentOpen,
    }));
  };

  return (
    <div className="mx-auto w-full max-w-(--thread-max-width) px-2 py-2">
      <ChainOfThought>
        {steps.map((step, index) => {
          const effectiveStatus = getEffectiveStatus(step);
          const icon = getStepIcon(effectiveStatus, step.title);
          const isOpen = getStepOpenState(step, index);
          return (
            <ChainOfThoughtStep
              key={step.id}
              open={isOpen}
              onOpenChange={() => handleToggle(step.id, isOpen)}
            >
              <ChainOfThoughtTrigger
                leftIcon={icon}
                swapIconOnHover={effectiveStatus !== "in_progress"}
                className={cn(
                  effectiveStatus === "in_progress" &&
                    "text-foreground font-medium",
                  effectiveStatus === "completed" && "text-muted-foreground",
                )}
              >
                {step.title}
              </ChainOfThoughtTrigger>
              {step.items && step.items.length > 0 && (
                <ChainOfThoughtContent>
                  {step.items.map((item, idx) => (
                    <ChainOfThoughtItem key={`${step.id}-item-${idx}`}>
                      {item}
                    </ChainOfThoughtItem>
                  ))}
                </ChainOfThoughtContent>
              )}
            </ChainOfThoughtStep>
          );
        })}
      </ChainOfThought>
    </div>
  );
};

/**
 * Component that handles auto-scroll when thinking steps update.
 * Uses useThreadViewport to scroll to bottom when thinking steps change,
 * ensuring the user always sees the latest content during streaming.
 */
const ThinkingStepsScrollHandler: FC = () => {
  const thinkingStepsMap = useContext(ThinkingStepsContext);
  const viewport = useThreadViewport();
  const isRunning = useAssistantState(({ thread }) => thread.isRunning);
  // Track the serialized state to detect any changes
  const prevStateRef = useRef<string>("");

  useEffect(() => {
    // Only act during streaming
    if (!isRunning) {
      prevStateRef.current = "";
      return;
    }

    // Serialize the thinking steps state to detect any changes
    // This catches new steps, status changes, and item additions
    let stateString = "";
    thinkingStepsMap.forEach((steps, msgId) => {
      steps.forEach((step) => {
        stateString += `${msgId}:${step.id}:${step.status}:${step.items?.length || 0};`;
      });
    });

    // If state changed at all during streaming, scroll
    if (stateString !== prevStateRef.current && stateString !== "") {
      prevStateRef.current = stateString;

      // Multiple attempts to ensure scroll happens after DOM updates
      const scrollAttempt = () => {
        try {
          viewport.scrollToBottom();
        } catch {
          // Ignore errors - viewport might not be ready
        }
      };

      // Delayed attempts to handle async DOM updates
      requestAnimationFrame(scrollAttempt);
      setTimeout(scrollAttempt, 100);
    }
  }, [thinkingStepsMap, viewport, isRunning]);

  return null; // This component doesn't render anything
};

export const Thread: FC<ThreadProps> = ({
  messageThinkingSteps = new Map(),
  header,
  mentionedDocuments = [],
  onMentionedDocumentsChange = () => {},
  spaceId,
}) => {
  const documentMentionValue = useMemo(
    () => ({
      mentionedDocuments,
      onMentionedDocumentsChange,
      spaceId,
    }),
    [mentionedDocuments, onMentionedDocumentsChange, spaceId],
  );

  return (
    <ThinkingStepsContext.Provider value={messageThinkingSteps}>
      <DocumentMentionContext.Provider value={documentMentionValue}>
        <ThreadPrimitive.Root
          className="aui-root aui-thread-root @container flex h-full min-h-0 flex-col bg-background"
          style={{
            ["--thread-max-width" as string]: "44rem",
          }}
        >
          <ThreadPrimitive.Viewport
            turnAnchor="top"
            className="aui-thread-viewport relative flex flex-1 min-h-0 flex-col overflow-x-auto overflow-y-scroll scroll-smooth px-4 pt-4"
          >
            {/* Optional sticky header for model selector etc. */}
            {header && <div className="sticky top-0 z-10 mb-4">{header}</div>}

            <AssistantIf condition={({ thread }) => thread.isEmpty}>
              <ThreadWelcome />
            </AssistantIf>

            <ThreadPrimitive.Messages
              components={{
                UserMessage,
                EditComposer,
                AssistantMessage,
              }}
            />

            <ThreadPrimitive.ViewportFooter className="aui-thread-viewport-footer sticky bottom-0 mx-auto mt-auto flex w-full max-w-(--thread-max-width) flex-col gap-4 overflow-visible rounded-t-3xl bg-background pb-4 md:pb-6">
              <ThreadScrollToBottom />
              <AssistantIf condition={({ thread }) => !thread.isEmpty}>
                <div className="fade-in slide-in-from-bottom-4 animate-in duration-500 ease-out fill-mode-both">
                  <Composer />
                </div>
              </AssistantIf>
            </ThreadPrimitive.ViewportFooter>
          </ThreadPrimitive.Viewport>
        </ThreadPrimitive.Root>
      </DocumentMentionContext.Provider>
    </ThinkingStepsContext.Provider>
  );
};

const ThreadScrollToBottom: FC = () => {
  const { t } = useTranslation();

  return (
    <ThreadPrimitive.ScrollToBottom asChild>
      <TooltipIconButton
        tooltip={t("spaces.chats.thread.scrollToBottom")}
        variant="outline"
        className="aui-thread-scroll-to-bottom -top-12 absolute z-10 self-center rounded-full p-4 disabled:invisible dark:bg-background dark:hover:bg-accent"
      >
        <ArrowDownIcon />
      </TooltipIconButton>
    </ThreadPrimitive.ScrollToBottom>
  );
};

const getTimeBasedGreeting = (userEmail?: string): string => {
  const hour = new Date().getHours();

  // Extract first name from email if available
  const firstName = userEmail
    ? userEmail.split("@")[0].split(".")[0].charAt(0).toUpperCase() +
      userEmail.split("@")[0].split(".")[0].slice(1)
    : null;

  // Array of greeting variations for each time period
  const morningGreetings = [
    "Good morning",
    "Rise and shine",
    "Morning",
    "Hey there",
  ];

  const afternoonGreetings = [
    "Good afternoon",
    "Afternoon",
    "Hey there",
    "Hi there",
  ];

  const eveningGreetings = ["Good evening", "Evening", "Hey there", "Hi there"];

  const nightGreetings = ["Good night", "Evening", "Hey there", "Winding down"];

  const lateNightGreetings = [
    "Still up",
    "Night owl mode",
    "The night is young",
    "Hi there",
  ];

  // Select a random greeting based on time
  let greeting: string;
  if (hour < 5) {
    // Late night: midnight to 5 AM
    greeting =
      lateNightGreetings[Math.floor(Math.random() * lateNightGreetings.length)];
  } else if (hour < 12) {
    greeting =
      morningGreetings[Math.floor(Math.random() * morningGreetings.length)];
  } else if (hour < 18) {
    greeting =
      afternoonGreetings[Math.floor(Math.random() * afternoonGreetings.length)];
  } else if (hour < 22) {
    greeting =
      eveningGreetings[Math.floor(Math.random() * eveningGreetings.length)];
  } else {
    // Night: 10 PM to midnight
    greeting =
      nightGreetings[Math.floor(Math.random() * nightGreetings.length)];
  }

  // Add personalization with first name if available
  if (firstName) {
    return `${greeting}, ${firstName}!`;
  }

  return `${greeting}!`;
};

const ThreadWelcome: FC = () => {
  // TODO: Get current user from Langflow auth store
  // const user = useAuthStore((state) => state.userData);
  const userEmail = undefined; // Placeholder

  // Memoize greeting so it doesn't change on re-renders (only on user change)
  const greeting = useMemo(() => getTimeBasedGreeting(userEmail), [userEmail]);

  return (
    <div className="aui-thread-welcome-root mx-auto flex w-full max-w-(--thread-max-width) grow flex-col items-center px-4 relative">
      {/* Greeting positioned above the composer - fixed position */}
      <div className="aui-thread-welcome-message absolute bottom-[calc(50%+5rem)] left-0 right-0 flex flex-col items-center text-center">
        <h1 className="aui-thread-welcome-message-inner fade-in slide-in-from-bottom-2 animate-in text-5xl delay-100 duration-500 ease-out fill-mode-both">
          {greeting}
        </h1>
      </div>
      {/* Composer - top edge fixed, expands downward only */}
      <div className="fade-in slide-in-from-bottom-3 animate-in delay-200 duration-500 ease-out fill-mode-both w-full flex items-start justify-center absolute top-[calc(50%-3.5rem)] left-0 right-0">
        <Composer />
      </div>
    </div>
  );
};

const Composer: FC = () => {
  const documentMentionContext = useContext(DocumentMentionContext);
  const mentionedDocuments = documentMentionContext?.mentionedDocuments || [];
  const onMentionedDocumentsChange =
    documentMentionContext?.onMentionedDocumentsChange;
  const spaceId = documentMentionContext?.spaceId;

  const [showDocumentPopover, setShowDocumentPopover] = useState(false);
  const [mentionQuery, setMentionQuery] = useState("");
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const [cursorPosition, setCursorPosition] = useState(0);

  const handleKeyUp = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (!spaceId || !onMentionedDocumentsChange) return;

    const target = e.currentTarget;
    const cursorPos = target.selectionStart || 0;
    const text = target.value;

    // Find @ symbol before cursor
    let atIndex = -1;
    for (let i = cursorPos - 1; i >= 0; i--) {
      if (text[i] === "@") {
        atIndex = i;
        break;
      }
      if (text[i] === " " || text[i] === "\n") {
        break;
      }
    }

    if (atIndex !== -1) {
      const query = text.slice(atIndex + 1, cursorPos);
      setMentionQuery(query);
      setShowDocumentPopover(true);
      setCursorPosition(atIndex);
    } else {
      setShowDocumentPopover(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Escape" && showDocumentPopover) {
      setShowDocumentPopover(false);
      e.preventDefault();
    }
  };

  const handleSelectDocument = (document: any) => {
    if (!inputRef.current || !onMentionedDocumentsChange) return;

    // Add document to mentioned documents
    if (!mentionedDocuments.find((d) => d.id === document.id)) {
      onMentionedDocumentsChange([...mentionedDocuments, document]);
    }

    // Remove @ mention from input
    const target = inputRef.current;
    const text = target.value;
    const beforeAt = text.slice(0, cursorPosition);
    const afterCursor = text.slice(target.selectionStart || 0);
    target.value = beforeAt + afterCursor;

    setShowDocumentPopover(false);
    setMentionQuery("");
  };

  const handleRemoveDocument = (documentId: number) => {
    if (!onMentionedDocumentsChange) return;
    onMentionedDocumentsChange(
      mentionedDocuments.filter((d) => d.id !== documentId),
    );
  };

  return (
    <ComposerPrimitive.Root className="aui-composer-root relative flex w-full flex-col">
      <ComposerPrimitive.AttachmentDropzone className="aui-composer-attachment-dropzone flex w-full flex-col rounded-2xl border-input bg-muted px-1 pt-2 outline-none transition-shadow data-[dragging=true]:border-ring data-[dragging=true]:border-dashed data-[dragging=true]:bg-accent/50">
        <ComposerAttachments />

        {/* Document mention badges */}
        {mentionedDocuments.length > 0 && (
          <div className="flex flex-wrap gap-1.5 px-3 pt-2">
            {mentionedDocuments.map((doc) => (
              <DocumentMentionBadge
                key={doc.id}
                document={doc}
                onRemove={() => handleRemoveDocument(doc.id)}
              />
            ))}
          </div>
        )}

        {/* Input field */}
        <div className="aui-composer-input-wrapper flex flex-wrap items-center gap-1.5 px-3 pt-2 pb-6">
          {/* Text input */}
          <ComposerPrimitive.Input
            ref={inputRef}
            onKeyUp={handleKeyUp}
            onKeyDown={handleKeyDown}
            placeholder="Ask Langflow..."
            className="aui-composer-input flex-1 min-w-[120px] max-h-32 resize-none bg-transparent text-sm outline-none placeholder:text-muted-foreground focus-visible:ring-0 py-1"
            rows={1}
            autoFocus
            aria-label="Message input"
          />
        </div>

        {/* Document mention popover */}
        {spaceId && showDocumentPopover && (
          <DocumentMentionPopover
            spaceId={spaceId}
            open={showDocumentPopover}
            onOpenChange={setShowDocumentPopover}
            onSelectDocument={handleSelectDocument}
            query={mentionQuery}
          />
        )}

        <ComposerAction />
      </ComposerPrimitive.AttachmentDropzone>
    </ComposerPrimitive.Root>
  );
};

const ComposerAction: FC = () => {
  // Check if any attachments are still being processed (running AND progress < 100)
  const hasProcessingAttachments = useAssistantState(({ composer }) =>
    composer.attachments?.some((att) => {
      const status = att.status;
      if (status?.type !== "running") return false;
      const progress = (status as { type: "running"; progress?: number })
        .progress;
      return progress === undefined || progress < 100;
    }),
  );

  // Check if composer text is empty
  const isComposerEmpty = useAssistantState(({ composer }) => {
    const text = composer.text?.trim() || "";
    return text.length === 0;
  });

  // TODO: Check if a model is configured from Langflow settings
  const hasModelConfigured = true; // Placeholder - assume model is configured

  const isSendDisabled =
    hasProcessingAttachments || isComposerEmpty || !hasModelConfigured;

  return (
    <div className="aui-composer-action-wrapper relative mx-2 mb-2 flex items-center justify-between">
      <div className="flex items-center gap-1">
        <ComposerAddAttachment />
      </div>

      {/* Show processing indicator when attachments are being processed */}
      {hasProcessingAttachments && (
        <div className="flex items-center gap-1.5 text-muted-foreground text-xs">
          <Loader2 className="size-3 animate-spin" />
          <span>Processing...</span>
        </div>
      )}

      {/* Show warning when no model is configured */}
      {!hasModelConfigured && !hasProcessingAttachments && (
        <div className="flex items-center gap-1.5 text-amber-600 dark:text-amber-400 text-xs">
          <AlertCircle className="size-3" />
          <span>Select a model</span>
        </div>
      )}

      <AssistantIf condition={({ thread }) => !thread.isRunning}>
        <ComposerPrimitive.Send asChild disabled={isSendDisabled}>
          <TooltipIconButton
            tooltip={
              !hasModelConfigured
                ? "Please select a model to start chatting"
                : hasProcessingAttachments
                  ? "Wait for attachments to process"
                  : isComposerEmpty
                    ? "Enter a message to send"
                    : "Send message"
            }
            side="bottom"
            type="submit"
            variant="default"
            size="icon"
            className={cn(
              "aui-composer-send size-8 rounded-full",
              isSendDisabled && "cursor-not-allowed opacity-50",
            )}
            aria-label="Send message"
            disabled={isSendDisabled}
          >
            <ArrowUpIcon className="aui-composer-send-icon size-4" />
          </TooltipIconButton>
        </ComposerPrimitive.Send>
      </AssistantIf>

      <AssistantIf condition={({ thread }) => thread.isRunning}>
        <ComposerPrimitive.Cancel asChild>
          <Button
            type="button"
            variant="default"
            size="icon"
            className="aui-composer-cancel size-8 rounded-full"
            aria-label="Stop generating"
          >
            <SquareIcon className="aui-composer-cancel-icon size-3 fill-current" />
          </Button>
        </ComposerPrimitive.Cancel>
      </AssistantIf>
    </div>
  );
};

const MessageError: FC = () => {
  return (
    <MessagePrimitive.Error>
      <ErrorPrimitive.Root className="aui-message-error-root mt-2 rounded-md border border-destructive bg-destructive/10 p-3 text-destructive text-sm dark:bg-destructive/5 dark:text-red-200">
        <ErrorPrimitive.Message className="aui-message-error-message line-clamp-2" />
      </ErrorPrimitive.Root>
    </MessagePrimitive.Error>
  );
};

/**
 * Custom component to render thinking steps from Context
 */
const ThinkingStepsPart: FC = () => {
  const thinkingStepsMap = useContext(ThinkingStepsContext);

  // Get the current message ID to look up thinking steps
  const messageId = useAssistantState(({ message }) => message?.id);
  const thinkingSteps = thinkingStepsMap.get(messageId) || [];

  // Check if thread is still running (for stopping the spinner when cancelled)
  const isThreadRunning = useAssistantState(({ thread }) => thread.isRunning);

  if (thinkingSteps.length === 0) return null;

  return (
    <div className="mb-3">
      <ThinkingStepsDisplay
        steps={thinkingSteps}
        isThreadRunning={isThreadRunning}
      />
    </div>
  );
};

const AssistantMessageInner: FC = () => {
  return (
    <>
      {/* Render thinking steps from message content - this ensures proper scroll tracking */}
      <ThinkingStepsPart />

      <div className="aui-assistant-message-content wrap-break-word px-2 text-foreground leading-relaxed">
        <MessagePrimitive.Parts
          components={{
            Text: MarkdownText,
            tools: { Fallback: ToolFallback },
          }}
        />
        <MessageError />
      </div>

      <div className="aui-assistant-message-footer mt-1 ml-2 flex">
        <BranchPicker />
        <AssistantActionBar />
      </div>
    </>
  );
};

const AssistantMessage: FC = () => {
  return (
    <MessagePrimitive.Root
      className="aui-assistant-message-root fade-in slide-in-from-bottom-1 relative mx-auto w-full max-w-(--thread-max-width) animate-in py-3 duration-150"
      data-role="assistant"
    >
      <AssistantMessageInner />
    </MessagePrimitive.Root>
  );
};

const AssistantActionBar: FC = () => {
  const { t } = useTranslation();

  return (
    <ActionBarPrimitive.Root
      hideWhenRunning
      autohide="not-last"
      autohideFloat="single-branch"
      className="aui-assistant-action-bar-root -ml-1 col-start-3 row-start-2 flex gap-1 text-muted-foreground data-floating:absolute data-floating:rounded-md data-floating:border data-floating:bg-background data-floating:p-1 data-floating:shadow-sm"
    >
      <ActionBarPrimitive.Copy asChild>
        <TooltipIconButton tooltip={t("spaces.chats.thread.copy")}>
          <AssistantIf condition={({ message }) => message.isCopied}>
            <CheckIcon />
          </AssistantIf>
          <AssistantIf condition={({ message }) => !message.isCopied}>
            <CopyIcon />
          </AssistantIf>
        </TooltipIconButton>
      </ActionBarPrimitive.Copy>
      <ActionBarPrimitive.ExportMarkdown asChild>
        <TooltipIconButton tooltip={t("spaces.chats.thread.exportAsMarkdown")}>
          <DownloadIcon />
        </TooltipIconButton>
      </ActionBarPrimitive.ExportMarkdown>
      <ActionBarPrimitive.Reload asChild>
        <TooltipIconButton tooltip={t("spaces.chats.thread.refresh")}>
          <RefreshCwIcon />
        </TooltipIconButton>
      </ActionBarPrimitive.Reload>
    </ActionBarPrimitive.Root>
  );
};

const UserMessage: FC = () => {
  // TODO: Implement document mentions display when documents store is available
  const mentionedDocs = undefined; // Placeholder

  return (
    <MessagePrimitive.Root
      className="aui-user-message-root fade-in slide-in-from-bottom-1 mx-auto grid w-full max-w-(--thread-max-width) animate-in auto-rows-auto grid-cols-[minmax(72px,1fr)_auto] content-start gap-y-2 px-2 py-3 duration-150 [&:where(>*)]:col-start-2"
      data-role="user"
    >
      <UserMessageAttachments />

      <div className="aui-user-message-content-wrapper relative col-start-2 min-w-0">
        <div className="aui-user-message-content wrap-break-word rounded-2xl bg-muted px-4 py-2.5 text-foreground">
          <MessagePrimitive.Parts />
        </div>
        <div className="aui-user-action-bar-wrapper -translate-x-full -translate-y-full absolute top-full left-0 pr-2">
          <UserActionBar />
        </div>
      </div>

      <BranchPicker className="aui-user-branch-picker -mr-1 col-span-full col-start-1 row-start-3 justify-end" />
    </MessagePrimitive.Root>
  );
};

const UserActionBar: FC = () => {
  const { t } = useTranslation();

  return (
    <ActionBarPrimitive.Root
      hideWhenRunning
      autohide="not-last"
      className="aui-user-action-bar-root flex flex-col items-end"
    >
      <ActionBarPrimitive.Edit asChild>
        <TooltipIconButton
          tooltip={t("spaces.chats.thread.edit")}
          className="aui-user-action-edit p-4"
        >
          <PencilIcon />
        </TooltipIconButton>
      </ActionBarPrimitive.Edit>
    </ActionBarPrimitive.Root>
  );
};

const EditComposer: FC = () => {
  const { t } = useTranslation();

  return (
    <MessagePrimitive.Root className="aui-edit-composer-wrapper mx-auto flex w-full max-w-(--thread-max-width) flex-col px-2 py-3">
      <ComposerPrimitive.Root className="aui-edit-composer-root ml-auto flex w-full max-w-[85%] flex-col rounded-2xl bg-muted">
        <ComposerPrimitive.Input
          className="aui-edit-composer-input min-h-14 w-full resize-none bg-transparent p-4 text-foreground text-sm outline-none"
          autoFocus
        />
        <div className="aui-edit-composer-footer mx-3 mb-3 flex items-center gap-2 self-end">
          <ComposerPrimitive.Cancel asChild>
            <Button variant="ghost" size="sm">
              {t("spaces.chats.thread.cancel")}
            </Button>
          </ComposerPrimitive.Cancel>
          <ComposerPrimitive.Send asChild>
            <Button size="sm">{t("spaces.chats.thread.update")}</Button>
          </ComposerPrimitive.Send>
        </div>
      </ComposerPrimitive.Root>
    </MessagePrimitive.Root>
  );
};

const BranchPicker: FC<BranchPickerPrimitive.Root.Props> = ({
  className,
  ...rest
}) => {
  const { t } = useTranslation();

  return (
    <BranchPickerPrimitive.Root
      hideWhenSingleBranch
      className={cn(
        "aui-branch-picker-root -ml-2 mr-2 inline-flex items-center text-muted-foreground text-xs",
        className,
      )}
      {...rest}
    >
      <BranchPickerPrimitive.Previous asChild>
        <TooltipIconButton tooltip={t("spaces.chats.thread.previous")}>
          <ChevronLeftIcon />
        </TooltipIconButton>
      </BranchPickerPrimitive.Previous>
      <span className="aui-branch-picker-state font-medium">
        <BranchPickerPrimitive.Number /> / <BranchPickerPrimitive.Count />
      </span>
      <BranchPickerPrimitive.Next asChild>
        <TooltipIconButton tooltip={t("spaces.chats.thread.next")}>
          <ChevronRightIcon />
        </TooltipIconButton>
      </BranchPickerPrimitive.Next>
    </BranchPickerPrimitive.Root>
  );
};
