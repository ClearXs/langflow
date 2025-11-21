import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import IconComponent from "@/components/common/genericIconComponent";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  useGetGlobalVariables,
  useGetSystemVariables,
} from "@/controllers/API/queries/variables";
import BaseModal from "@/modals/baseModal";

interface RuntimeVariable {
  key: string;
  value: string;
}

interface RuntimeVariablesModalProps {
  open: boolean;
  setOpen: (open: boolean) => void;
  onConfirm: (variables: Record<string, string>) => void;
}

export default function RuntimeVariablesModal({
  open,
  setOpen,
  onConfirm,
}: RuntimeVariablesModalProps) {
  const { t } = useTranslation();
  const { data: globalVariables } = useGetGlobalVariables();
  const { data: systemVariables } = useGetSystemVariables();

  const [variables, setVariables] = useState<RuntimeVariable[]>([
    { key: "", value: "" },
  ]);
  const [isVariablesOpen, setIsVariablesOpen] = useState(false);

  // Merge all variables for display
  const allVariables = useMemo(() => {
    const global = (globalVariables || []).map((v) => ({
      name: v.name,
      displayName: `${v.name} [${t("variable.globalTag")}]`,
      description: v.description,
      isSystem: false,
    }));

    const system = (systemVariables || []).map((v) => ({
      name: v.name,
      displayName: `${v.name} [${t("variable.systemTag")}]`,
      description: v.display_name || v.description,
      example: v.example,
      isSystem: true,
    }));

    return [...system, ...global];
  }, [globalVariables, systemVariables, t]);

  // Get all available variable names for suggestions
  const allVariableNames = useMemo(() => {
    return allVariables.map((v) => v.name);
  }, [allVariables]);

  const handleAddRow = () => {
    setVariables([...variables, { key: "", value: "" }]);
  };

  const handleRemoveRow = (index: number) => {
    const newVariables = variables.filter((_, i) => i !== index);
    setVariables(
      newVariables.length > 0 ? newVariables : [{ key: "", value: "" }],
    );
  };

  const handleKeyChange = (index: number, key: string) => {
    const newVariables = [...variables];
    newVariables[index].key = key;
    setVariables(newVariables);
  };

  const handleValueChange = (index: number, value: string) => {
    const newVariables = [...variables];
    newVariables[index].value = value;
    setVariables(newVariables);
  };

  const handleConfirm = () => {
    // Filter out empty rows and convert to Record
    const result: Record<string, string> = {};
    variables.forEach((v) => {
      if (v.key.trim() && v.value.trim()) {
        result[v.key.trim()] = v.value.trim();
      }
    });

    onConfirm(result);
    setOpen(false);
    // Reset to initial state
    setVariables([{ key: "", value: "" }]);
  };

  const handleCancel = () => {
    setOpen(false);
    // Reset to initial state
    setVariables([{ key: "", value: "" }]);
  };

  return (
    <BaseModal open={open} setOpen={setOpen} size="medium">
      <BaseModal.Header description={t("variable.runtime.description")}>
        <div className="flex items-center gap-2">
          <IconComponent name="PlayCircle" className="h-5 w-5" />
          <span>{t("variable.runtime.title")}</span>
        </div>
      </BaseModal.Header>
      <BaseModal.Content>
        <div className="flex flex-col gap-4">
          {/* Variable usage hint with collapsible list */}
          <Collapsible
            open={isVariablesOpen}
            onOpenChange={setIsVariablesOpen}
            className="rounded-md bg-muted"
          >
            <div className="flex items-center gap-2 px-3 py-2">
              <IconComponent
                name="Info"
                className="h-3.5 w-3.5 flex-shrink-0"
              />
              <div className="flex-1 text-xs">
                <span className="text-muted-foreground">
                  {t("variable.runtime.hint")}
                </span>
                {allVariables.length > 0 && (
                  <span className="ml-2 font-mono text-muted-foreground">
                    {t("variable.runtime.availableCount", {
                      count: allVariables.length,
                    })}
                  </span>
                )}
              </div>
              {allVariables.length > 0 && (
                <CollapsibleTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0"
                    type="button"
                  >
                    <IconComponent
                      name={isVariablesOpen ? "ChevronUp" : "ChevronDown"}
                      className="h-3.5 w-3.5"
                    />
                  </Button>
                </CollapsibleTrigger>
              )}
            </div>

            {allVariables.length > 0 && (
              <CollapsibleContent>
                <div className="border-t border-border px-3 py-2">
                  <div className="max-h-40 space-y-1 overflow-y-auto text-xs">
                    {allVariables.map((variable, index) => (
                      <div
                        key={index}
                        className="flex items-start gap-2 rounded px-2 py-1 hover:bg-background/50"
                      >
                        <code className="font-mono text-primary">
                          {variable.name}
                        </code>
                        <span className="flex-1 text-muted-foreground">
                          {variable.description}
                        </span>
                        {variable.example && (
                          <span className="text-xs text-muted-foreground/70">
                            {t("common.example")}: {variable.example}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </CollapsibleContent>
            )}
          </Collapsible>

          {/* Table Header */}
          <div className="grid grid-cols-[1fr_1fr_auto] gap-2 px-2 text-sm font-medium text-muted-foreground">
            <div>{t("variable.runtime.key")}</div>
            <div>{t("variable.runtime.value")}</div>
            <div className="w-8" />
          </div>

          <Separator />

          {/* Table Rows */}
          <ScrollArea className="max-h-[400px]">
            <div className="flex flex-col gap-2">
              {variables.map((variable, index) => (
                <div
                  key={index}
                  className="grid grid-cols-[1fr_1fr_auto] gap-2 items-center"
                >
                  <Input
                    placeholder={t("variable.runtime.key")}
                    value={variable.key}
                    onChange={(e) => handleKeyChange(index, e.target.value)}
                    list={`variable-suggestions-${index}`}
                  />
                  <datalist id={`variable-suggestions-${index}`}>
                    {allVariableNames.map((name) => (
                      <option key={name} value={name} />
                    ))}
                  </datalist>

                  <Input
                    placeholder={t("variable.runtime.value")}
                    value={variable.value}
                    onChange={(e) => handleValueChange(index, e.target.value)}
                  />

                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleRemoveRow(index)}
                    disabled={variables.length === 1}
                    className="h-9 w-9"
                  >
                    <IconComponent name="Trash2" className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          </ScrollArea>

          {/* Add Row Button */}
          <Button variant="outline" onClick={handleAddRow} className="w-full">
            <IconComponent name="Plus" className="mr-2 h-4 w-4" />
            {t("variable.runtime.addRow")}
          </Button>
        </div>
      </BaseModal.Content>
      <BaseModal.Footer>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleCancel}>
            {t("variable.runtime.cancel")}
          </Button>
          <Button onClick={handleConfirm}>
            <IconComponent name="Play" className="mr-2 h-4 w-4" />
            {t("variable.runtime.run")}
          </Button>
        </div>
      </BaseModal.Footer>
    </BaseModal>
  );
}
