"use client";

import { FileText, Loader2, Search } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import { type Document, searchDocuments } from "@/services/documentService";

export interface DocumentMentionPopoverProps {
  spaceId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelectDocument: (document: Document) => void;
  query?: string;
}

export function DocumentMentionPopover({
  spaceId,
  open,
  onOpenChange,
  onSelectDocument,
  query = "",
}: DocumentMentionPopoverProps) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState(query);

  // Debounce search
  const searchTimeoutRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    if (!open) return;

    const performSearch = async () => {
      if (!spaceId) return;

      setIsLoading(true);
      try {
        const results = await searchDocuments(spaceId, searchQuery.trim(), 10);
        setDocuments(results);
      } catch (error) {
        console.error("[DocumentMentionPopover] Search failed:", error);
        setDocuments([]);
      } finally {
        setIsLoading(false);
      }
    };

    // Debounce search
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    searchTimeoutRef.current = setTimeout(() => {
      performSearch();
    }, 300);

    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, [spaceId, searchQuery, open]);

  // Update search query when external query prop changes
  useEffect(() => {
    if (query !== searchQuery) {
      setSearchQuery(query);
    }
  }, [query]);

  return (
    <Popover open={open} onOpenChange={onOpenChange}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="h-8 w-8 p-0"
          aria-label="Mention document"
        >
          <FileText className="h-4 w-4" />
        </Button>
      </PopoverTrigger>
      <PopoverContent
        className="w-80 p-0"
        align="start"
        side="top"
        sideOffset={8}
      >
        <Command shouldFilter={false}>
          <CommandInput
            placeholder="Search documents..."
            value={searchQuery}
            onValueChange={setSearchQuery}
          />
          <CommandList>
            {isLoading ? (
              <div className="flex items-center justify-center p-4">
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                <span className="ml-2 text-sm text-muted-foreground">
                  Searching...
                </span>
              </div>
            ) : documents.length === 0 ? (
              <CommandEmpty>
                {searchQuery.trim()
                  ? "No documents found"
                  : "Start typing to search documents"}
              </CommandEmpty>
            ) : (
              <CommandGroup heading="Documents">
                {documents.map((doc) => (
                  <CommandItem
                    key={doc.id}
                    value={doc.id.toString()}
                    onSelect={() => {
                      onSelectDocument(doc);
                      onOpenChange(false);
                    }}
                  >
                    <FileText className="mr-2 h-4 w-4 text-muted-foreground" />
                    <div className="flex-1 overflow-hidden">
                      <div className="truncate font-medium">{doc.title}</div>
                      <div className="truncate text-xs text-muted-foreground">
                        {doc.document_type}
                      </div>
                    </div>
                  </CommandItem>
                ))}
              </CommandGroup>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

/**
 * Document mention badge component
 * Shows a mentioned document as a badge/chip
 */
export interface DocumentMentionBadgeProps {
  document: Document;
  onRemove?: () => void;
  className?: string;
}

export function DocumentMentionBadge({
  document,
  onRemove,
  className,
}: DocumentMentionBadgeProps) {
  return (
    <div
      className={cn(
        "inline-flex items-center gap-1 rounded-md bg-primary/10 px-2 py-1 text-xs font-medium text-primary",
        className,
      )}
    >
      <FileText className="h-3 w-3" />
      <span className="truncate max-w-[200px]">{document.title}</span>
      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          className="ml-1 rounded-sm hover:bg-primary/20"
          aria-label="Remove mention"
        >
          <span className="sr-only">Remove</span>
          <svg
            className="h-3 w-3"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      )}
    </div>
  );
}
