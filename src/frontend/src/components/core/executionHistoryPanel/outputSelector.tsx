import { useTranslation } from "react-i18next";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { ExecutionOutput } from "./useExecutionData";

interface OutputSelectorProps {
  outputs: ExecutionOutput[];
  selectedIndex: number;
  onSelect: (index: number) => void;
}

export default function OutputSelector({
  outputs,
  selectedIndex,
  onSelect,
}: OutputSelectorProps) {
  const { t } = useTranslation();

  return (
    <div className="flex items-center gap-2">
      <label className="whitespace-nowrap text-xs text-muted-foreground">
        {t("executionHistory.selectOutput")}:
      </label>
      <Select
        value={selectedIndex.toString()}
        onValueChange={(value) => onSelect(parseInt(value, 10))}
      >
        <SelectTrigger className="h-7 w-[150px] text-xs">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {outputs.map((output, index) => (
            <SelectItem key={output.name} value={index.toString()}>
              {output.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
