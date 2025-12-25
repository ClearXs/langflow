import { Panel, useStoreApi } from "@xyflow/react";
import { type ReactNode, useEffect } from "react";
import { useShallow } from "zustand/react/shallow";
import { UploadProgressDrawer } from "@/components/core/fileTableView/components/UploadProgressDrawer";
import { Separator } from "@/components/ui/separator";
import { useIsEmbedded } from "@/hooks/use-iframe-params";
import useFlowStore from "@/stores/flowStore";
import { useUploadProgressStore } from "@/stores/uploadProgressStore";
import CanvasControlsDropdown from "./CanvasControlsDropdown";
import FileUploadButton from "./FileUploadButton";
import HelpDropdown from "./HelpDropdown";
import SettingsButton from "./SettingsButton";
import VariablesButton from "./VariablesButton";

const CanvasControls = ({ children }: { children?: ReactNode }) => {
  const reactFlowStoreApi = useStoreApi();
  const isFlowLocked = useFlowStore(
    useShallow((state) => state.currentFlow?.locked),
  );
  const isEmbedded = useIsEmbedded();

  // Upload progress store
  const {
    isDrawerOpen,
    toggleDrawer,
    setDrawerOpen,
    folders,
    tasks,
    activeUploads,
    totalCompleted,
    totalFailed,
    isRunning,
    uploadControls,
  } = useUploadProgressStore();

  const hasActiveUploads =
    activeUploads > 0 || tasks.some((t) => t.status === "uploading");

  useEffect(() => {
    reactFlowStoreApi.setState({
      nodesDraggable: !isFlowLocked,
      nodesConnectable: !isFlowLocked,
      elementsSelectable: !isFlowLocked,
    });
  }, [isFlowLocked, reactFlowStoreApi]);

  return (
    <>
      <Panel
        data-testid="main_canvas_controls"
        className="react-flow__controls !left-auto !m-2 flex !flex-row rounded-md border border-border bg-background fill-foreground stroke-foreground text-primary [&>button]:border-0"
        position="bottom-right"
      >
        {children}
        {children && (
          <span>
            <Separator orientation="vertical" />
          </span>
        )}
        <FileUploadButton
          onClick={toggleDrawer}
          hasActiveUploads={hasActiveUploads}
        />
        <span>
          <Separator orientation="vertical" />
        </span>
        <VariablesButton />
        <span>
          <Separator orientation="vertical" />
        </span>
        <CanvasControlsDropdown />
        <span>
          <Separator orientation="vertical" />
        </span>
        {isEmbedded ? <SettingsButton /> : <HelpDropdown />}
      </Panel>

      {/* Upload Progress Drawer */}
      <UploadProgressDrawer
        isOpen={isDrawerOpen}
        onClose={() => setDrawerOpen(false)}
        folders={folders}
        tasks={tasks}
        activeUploads={activeUploads}
        totalCompleted={totalCompleted}
        totalFailed={totalFailed}
        isRunning={isRunning}
        onPause={() => {
          uploadControls.pauseQueue?.();
        }}
        onResume={() => {
          uploadControls.startQueue?.();
        }}
        onCancel={(taskId) => {
          uploadControls.cancelTask?.(taskId);
        }}
        onRetry={(taskId) => {
          uploadControls.retryTask?.(taskId);
        }}
      />
    </>
  );
};

export default CanvasControls;
