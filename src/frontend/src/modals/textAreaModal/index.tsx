import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  useGetGlobalVariables,
  useGetSystemVariables,
} from "@/controllers/API/queries/variables";
import { useFormLocale } from "@/i18n/locale";
import IconComponent from "../../components/common/genericIconComponent";
import { Button } from "../../components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "../../components/ui/collapsible";
import { Textarea } from "../../components/ui/textarea";
import type { textModalPropsType } from "../../types/components";
import { handleKeyDown } from "../../utils/reactflowUtils";
import { classNames, cn } from "../../utils/utils";
import BaseModal from "../baseModal";

export default function ComponentTextModal({
  value,
  setValue,
  children,
  disabled,
  readonly = false,
  password,
  changeVisibility,
  onCloseModal,
}: textModalPropsType): JSX.Element {
  const [modalOpen, setModalOpen] = useState(false);
  const [inputValue, setInputValue] = useState(value);
  const { t } = useTranslation();

  const formLocale = useFormLocale();
  const { data: globalVariables } = useGetGlobalVariables();
  const { data: systemVariables } = useGetSystemVariables();

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

  const textRef = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    if (typeof value === "string") setInputValue(value);
  }, [value, modalOpen]);

  useEffect(() => {
    if (!modalOpen) {
      onCloseModal?.();
    }
  }, [modalOpen]);

  return (
    <BaseModal
      onChangeOpenModal={(open) => {}}
      open={modalOpen}
      setOpen={setModalOpen}
      size="x-large"
    >
      <BaseModal.Trigger disable={disabled} asChild>
        {children}
      </BaseModal.Trigger>
      <BaseModal.Header>
        <div className="flex w-full items-start gap-3">
          <div className="flex">
            <IconComponent
              name={"FileText"}
              className="h-6 w-6 pr-1 text-primary"
              aria-hidden="true"
            />
            <span className="pl-2" data-testid="modal-title">
              {formLocale.TEXT_DIALOG_TITLE}
            </span>
          </div>
          {password !== undefined && (
            <div>
              <button
                onClick={() => {
                  if (changeVisibility) changeVisibility();
                }}
              >
                <IconComponent
                  name={password ? "Eye" : "EyeOff"}
                  className="h-6 w-6 cursor-pointer text-primary"
                />
              </button>
            </div>
          )}
        </div>
      </BaseModal.Header>
      <BaseModal.Content overflowHidden>
        <div className="flex h-full w-full flex-col gap-2">
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
                  {t("variable.textArea.hint")}
                </span>
                {allVariables.length > 0 && (
                  <span className="ml-2 font-mono text-muted-foreground">
                    {t("variable.textArea.availableCount", {
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
                          {`{${variable.name}}`}
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

          <div className={classNames("flex h-full w-full rounded-lg border")}>
            <Textarea
              password={password}
              ref={textRef}
              className="form-input h-full w-full resize-none overflow-auto rounded-lg focus-visible:ring-1"
              value={inputValue}
              onChange={(event) => {
                setInputValue(event.target.value);
              }}
              placeholder={formLocale.EDIT_TEXT_PLACEHOLDER}
              onKeyDown={(e) => {
                handleKeyDown(e, value, "");
              }}
              readOnly={readonly}
              id={"text-area-modal"}
              data-testid={"text-area-modal"}
            />
          </div>
        </div>
      </BaseModal.Content>
      <BaseModal.Footer>
        <div className="flex w-full shrink-0 items-end justify-end">
          <Button
            data-testid="genericModalBtnSave"
            id="genericModalBtnSave"
            disabled={readonly}
            onClick={() => {
              setValue(inputValue);
              setModalOpen(false);
            }}
            type="submit"
          >
            {t("components.button.finishEditing")}
          </Button>
        </div>
      </BaseModal.Footer>
    </BaseModal>
  );
}
