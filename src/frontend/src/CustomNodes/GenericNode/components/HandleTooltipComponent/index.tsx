import { useTranslation } from "react-i18next";
import { convertTestName } from "@/components/common/storeCardComponent/utils/convert-test-name";
import { Badge } from "@/components/ui/badge";
import { nodeColorsName } from "@/utils/styleUtils";

export default function HandleTooltipComponent({
  isInput,
  tooltipTitle,
  isConnecting,
  isCompatible,
  isSameNode,
  left,
}: {
  isInput: boolean;
  tooltipTitle: string;
  isConnecting: boolean;
  isCompatible: boolean;
  isSameNode: boolean;
  left: boolean;
}) {
  const { t } = useTranslation();
  
  const tooltips = tooltipTitle.split("\n");
  const plural = tooltips.length > 1;

  return (
    <div className="font-medium">
      {isSameNode ? (
        t("components.handle.cantConnectSameNode")
      ) : (
        <div className="flex items-center gap-1.5">
          {isConnecting ? (
            isCompatible ? (
              <span>
                <span className="font-semibold">
                  {t("components.handle.connectTo")}
                </span>{" "}
                {t("components.handle.to")}
              </span>
            ) : (
              <span>{t("components.handle.incompatibleWith")}</span>
            )
          ) : (
            <span className="text-xs">
              {isInput
                ? plural
                  ? t("components.handle.inputTypes")
                  : t("components.handle.inputType")
                : plural
                  ? t("components.handle.outputTypes")
                  : t("components.handle.outputType")}
              :{" "}
            </span>
          )}
          {tooltips.map((word, index) => (
            <Badge
              className="h-6 rounded-md p-1"
              key={`${index}-${word.toLowerCase()}`}
              style={{
                backgroundColor: left
                  ? `hsl(var(--datatype-${nodeColorsName[word]}))`
                  : `hsl(var(--datatype-${nodeColorsName[word]}-foreground))`,
                color: left
                  ? `hsl(var(--datatype-${nodeColorsName[word]}-foreground))`
                  : `hsl(var(--datatype-${nodeColorsName[word]}))`,
              }}
              data-testid={`${isInput ? "input" : "output"}-tooltip-${convertTestName(word)}`}
            >
              {word}
            </Badge>
          ))}
          {isConnecting && (
            <span>
              {isInput
                ? t("components.handle.input")
                : t("components.handle.output")}
            </span>
          )}
        </div>
      )}
      {!isConnecting && (
        <div className="mt-2 flex flex-col gap-0.5 text-xs leading-6">
          <div>
            <b>{t("common.copy")}</b>{" "}
            {t("components.handle.dragToConnect")}{" "}
            {!isInput
              ? t("components.handle.inputs")
              : t("components.handle.outputs")}
          </div>
          <div>
            <b>{t("common.select")}</b>{" "}
            {t("components.handle.clickToFilter")}{" "}
            {!isInput
              ? t("components.handle.inputs")
              : t("components.handle.outputs")}{" "}
            {t("components.handle.andComponents")}
          </div>
        </div>
      )}
    </div>
  );
}