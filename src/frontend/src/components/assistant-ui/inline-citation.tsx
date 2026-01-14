"use client";

import type { FC } from "react";
import { useState } from "react";

// Note: SourceDetailPanel will need to be migrated separately
// For now, this is a simplified version that just shows the citation number
// TODO: Import SourceDetailPanel when it's migrated

interface InlineCitationProps {
  chunkId: number;
  citationNumber: number;
}

/**
 * Inline citation component for chat messages.
 * Renders a clickable numbered badge that shows source information.
 *
 * TODO: Integrate with SourceDetailPanel component once migrated.
 */
export const InlineCitation: FC<InlineCitationProps> = ({
  chunkId,
  citationNumber,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  // Simplified version - will be enhanced when SourceDetailPanel is migrated
  return (
    <span
      onClick={() => {
        // TODO: Open SourceDetailPanel when available
        console.log("Citation clicked:", { chunkId, citationNumber });
        setIsOpen(true);
      }}
      onKeyDown={(e) => {
        if (e.key === "Enter") {
          console.log("Citation activated:", { chunkId, citationNumber });
          setIsOpen(true);
        }
      }}
      className="text-[10px] font-bold bg-primary/80 hover:bg-primary text-primary-foreground rounded-full min-w-4 h-4 px-1 inline-flex items-center justify-center align-super cursor-pointer transition-colors ml-0.5"
      title={`View source #${citationNumber} (chunk ID: ${chunkId})`}
      role="button"
      tabIndex={0}
    >
      {citationNumber}
    </span>
  );
};
