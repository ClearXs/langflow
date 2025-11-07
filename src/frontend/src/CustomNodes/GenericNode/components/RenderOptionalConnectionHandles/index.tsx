import { useMemo } from "react";
import { Handle, Position } from "reactflow";
import IconComponent from "@/components/common/genericIconComponent";
import ShadTooltip from "@/components/common/shadTooltipComponent";
import { APIClassType } from "@/types/api";
import { NodeDataType } from "@/types/flow";

interface Props {
  data: NodeDataType;
  types: APIClassType;
}

export default function RenderOptionalConnectionHandles({
  data,
}: Props): JSX.Element | null {
  // Filter out optional connection fields
  const optionalFields = useMemo(() => {
    const template = data.node?.template || {};
    return Object.entries(template)
      .filter(([_, field]) => field?.input_group === "optional_connections")
      .map(([name, field]) => ({ name, ...field }));
  }, [data.node?.template]);

  if (optionalFields.length === 0) return null;

  return (
    <div className="flex flex-col gap-1">
      {optionalFields.map((field) => (
        <div key={field.name} className="relative flex items-center gap-2 py-1">
          {/* Compact Handle */}
          <ShadTooltip content={field.info || ""} side="left">
            <Handle
              type="target"
              position={Position.Left}
              id={field.name}
              className="!absolute !left-[-8px] !top-1/2 !-translate-y-1/2 optional-connection-handle"
              style={{
                width: "14px",
                height: "14px",
                border: "2px dashed hsl(var(--muted-foreground) / 0.3)",
                background: "hsl(var(--background))",
                opacity: 0.6,
                transition: "all 0.2s ease",
              }}
              onMouseEnter={(e) => {
                const target = e.currentTarget as HTMLElement;
                target.style.opacity = "1";
                target.style.borderColor = "hsl(var(--primary))";
                target.style.borderStyle = "solid";
                target.style.transform = "translateY(-50%) scale(1.15)";
              }}
              onMouseLeave={(e) => {
                const target = e.currentTarget as HTMLElement;
                target.style.opacity = "0.6";
                target.style.borderColor = "hsl(var(--muted-foreground) / 0.3)";
                target.style.borderStyle = "dashed";
                target.style.transform = "translateY(-50%) scale(1)";
              }}
            />
          </ShadTooltip>

          {/* Text Label */}
          <span className="text-xs text-muted-foreground/70 ml-3">
            {field.display_name || field.name}
          </span>

          {/* Info Icon */}
          {field.info && (
            <ShadTooltip content={field.info} side="right">
              <div className="cursor-help">
                <IconComponent
                  name="Info"
                  className="h-3 w-3 text-muted-foreground/40"
                />
              </div>
            </ShadTooltip>
          )}
        </div>
      ))}
    </div>
  );
}
