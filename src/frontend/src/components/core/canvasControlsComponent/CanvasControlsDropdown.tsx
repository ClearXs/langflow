import { useReactFlow, useStore } from "@xyflow/react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { shallow } from "zustand/shallow";
import IconComponent from "@/components/common/genericIconComponent";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Separator } from "@/components/ui/separator";
import DropdownControlButton from "./DropdownControlButton";
import { formatZoomPercentage, reactFlowSelector } from "./utils/canvasUtils";

export const KEYBOARD_SHORTCUTS = {
  ZOOM_IN: { key: "+", code: "Equal" },
  ZOOM_OUT: { key: "-", code: "Minus" },
  FIT_VIEW: { key: "1", code: "Digit1" },
  RESET_ZOOM: { key: "0", code: "Digit0" },
} as const;

const CanvasControlsDropdown = () => {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const { fitView, zoomIn, zoomOut, zoomTo } = useReactFlow();

  const { minZoomReached, maxZoomReached, zoom } = useStore(
    reactFlowSelector,
    shallow,
  );

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const isModifierPressed = event.metaKey || event.ctrlKey;

      if (!isModifierPressed) return;

      switch (event.code) {
        case KEYBOARD_SHORTCUTS.ZOOM_IN.code:
          event.preventDefault();
          if (!maxZoomReached) {
            zoomIn();
          }
          break;
        case KEYBOARD_SHORTCUTS.ZOOM_OUT.code:
          event.preventDefault();
          if (!minZoomReached) {
            zoomOut();
          }
          break;
        case KEYBOARD_SHORTCUTS.FIT_VIEW.code:
          event.preventDefault();
          fitView();
          break;
        case KEYBOARD_SHORTCUTS.RESET_ZOOM.code:
          event.preventDefault();
          zoomTo(1);
          break;
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [zoomIn, zoomOut, fitView, zoomTo, maxZoomReached, minZoomReached]);

  const handleZoomIn = useCallback(() => {
    zoomIn();
  }, [zoomIn]);

  const handleZoomOut = useCallback(() => {
    zoomOut();
  }, [zoomOut]);

  const handleFitView = useCallback(() => {
    fitView();
  }, [fitView]);

  const handleResetZoom = useCallback(() => {
    zoomTo(1);
  }, [zoomTo]);

  return (
    <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          data-testid="canvas_controls_dropdown"
          className="group rounded-none px-2 py-2 hover:bg-muted"
          unstyled
          title={t("canvas.controls.title")}
        >
          <div className="flex items-center justify-center ">
            <div className="text-sm pr-1 text-muted-foreground">
              {formatZoomPercentage(zoom)}
            </div>
            <IconComponent
              name={isOpen ? "ChevronDown" : "ChevronUp"}
              aria-hidden="true"
              className="text-muted-foreground group-hover:text-primary !h-5 !w-5"
            />
          </div>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        side="top"
        align="end"
        className="flex flex-col w-full"
      >
        <DropdownControlButton
          tooltipText={t("canvas.controls.zoomIn")}
          onClick={handleZoomIn}
          disabled={maxZoomReached}
          testId="zoom_in"
          label={t("canvas.controls.zoomIn")}
          shortcut={KEYBOARD_SHORTCUTS.ZOOM_IN.key}
        />
        <DropdownControlButton
          tooltipText={t("canvas.controls.zoomOut")}
          onClick={handleZoomOut}
          disabled={minZoomReached}
          testId="zoom_out"
          label={t("canvas.controls.zoomOut")}
          shortcut={KEYBOARD_SHORTCUTS.ZOOM_OUT.key}
        />
        <Separator />
        <DropdownControlButton
          tooltipText={t("canvas.controls.resetZoomTooltip")}
          onClick={handleResetZoom}
          testId="reset_zoom"
          label={t("canvas.controls.resetZoom")}
          shortcut={KEYBOARD_SHORTCUTS.RESET_ZOOM.key}
        />
        <DropdownControlButton
          tooltipText={t("canvas.controls.fitViewTooltip")}
          onClick={handleFitView}
          testId="fit_view"
          label={t("canvas.controls.fitView")}
          shortcut={KEYBOARD_SHORTCUTS.FIT_VIEW.key}
        />
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

export default CanvasControlsDropdown;