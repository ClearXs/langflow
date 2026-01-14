"use client";

import { useCallback, useState } from "react";
import type {
  GlobalLLMConfigRead,
  LLMConfigRead,
} from "@/types/api/llm-configs";
import { ModelSelector } from "./model-selector";

interface ChatHeaderProps {
  spaceId?: number;
  userConfigs?: LLMConfigRead[];
  globalConfigs?: GlobalLLMConfigRead[];
  currentConfig?: LLMConfigRead | GlobalLLMConfigRead | null;
  isLoading?: boolean;
  onSelectConfig?: (
    config: LLMConfigRead | GlobalLLMConfigRead,
  ) => Promise<void>;
  onEditConfig?: (
    config: LLMConfigRead | GlobalLLMConfigRead,
    isGlobal: boolean,
  ) => void;
  onAddNewConfig?: () => void;
}

export function ChatHeader({
  spaceId,
  userConfigs = [],
  globalConfigs = [],
  currentConfig = null,
  isLoading = false,
  onSelectConfig,
  onEditConfig,
  onAddNewConfig,
}: ChatHeaderProps) {
  // TODO: Implement model config sidebar when LLM config management is fully integrated
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleEditConfig = useCallback(
    (config: LLMConfigRead | GlobalLLMConfigRead, isGlobal: boolean) => {
      // For now, just call the parent handler
      // In the future, this will open a sidebar for editing
      if (onEditConfig) {
        onEditConfig(config, isGlobal);
      }
      // TODO: Uncomment when ModelConfigSidebar is migrated
      // setSidebarOpen(true);
    },
    [onEditConfig],
  );

  const handleAddNew = useCallback(() => {
    // For now, just call the parent handler
    // In the future, this will open a sidebar for creating
    if (onAddNewConfig) {
      onAddNewConfig();
    }
    // TODO: Uncomment when ModelConfigSidebar is migrated
    // setSidebarOpen(true);
  }, [onAddNewConfig]);

  return (
    <div className="flex items-center gap-2">
      <ModelSelector
        userConfigs={userConfigs}
        globalConfigs={globalConfigs}
        currentConfig={currentConfig}
        isLoading={isLoading}
        onSelectConfig={onSelectConfig}
        onEdit={handleEditConfig}
        onAddNew={handleAddNew}
      />

      {/* TODO: Add ModelConfigSidebar component when migrated */}
      {/* <ModelConfigSidebar
				open={sidebarOpen}
				onOpenChange={setSidebarOpen}
				config={selectedConfig}
				isGlobal={isGlobal}
				spaceId={spaceId}
				mode={sidebarMode}
			/> */}
    </div>
  );
}
