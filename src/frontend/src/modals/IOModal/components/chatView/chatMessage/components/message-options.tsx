import { type ButtonHTMLAttributes, useState } from "react";
import IconComponent from "@/components/common/genericIconComponent";
import ShadTooltip from "@/components/common/shadTooltipComponent";
import { Button } from "@/components/ui/button";
import { cn } from "@/utils/utils";
import { useTranslation } from "react-i18next";

export function EditMessageButton({
  onEdit,
  onCopy,
  onEvaluate,
  isBotMessage,
  evaluation,
  isAudioMessage,
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  onEdit?: () => void;
  onCopy: () => void;
  onEvaluate?: (value: boolean | null) => void;
  isBotMessage?: boolean;
  evaluation?: boolean | null;
  isAudioMessage?: boolean;
}) {
  const { t } = useTranslation();
  const [isCopied, setIsCopied] = useState(false);

  const handleCopy = () => {
    onCopy();
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  const handleEvaluate = (value: boolean) => {
    onEvaluate?.(evaluation === value ? null : value);
  };

  return (
    <div className="flex items-center rounded-md border border-border bg-background">
      {!isAudioMessage && onEdit && (
        <ShadTooltip styleClasses="z-50" content={t("chat.message.editMessage")} side="top">
          <div className="p-1">
            <Button
              variant="ghost"
              size="icon"
              onClick={onEdit}
              className="h-8 w-8"
            >
              <IconComponent name="Pen" className="h-4 w-4" />
            </Button>
          </div>
        </ShadTooltip>
      )}

      <ShadTooltip
        styleClasses="z-50"
        content={isCopied ? t("chat.message.copied") : t("chat.message.copyMessage")}
        side="top"
      >
        <div className="p-1">
          <Button
            variant="ghost"
            size="icon"
            onClick={handleCopy}
            className="h-8 w-8"
          >
            <IconComponent
              name={isCopied ? "Check" : "Copy"}
              className="h-4 w-4"
            />
          </Button>
        </div>
      </ShadTooltip>

      {isBotMessage && (
        <div className="flex">
          <ShadTooltip styleClasses="z-50" content={t("chat.message.helpful")} side="top">
            <div className="p-1">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => handleEvaluate(true)}
                className="h-8 w-8"
                data-testid="helpful-button"
              >
                <IconComponent
                  name={evaluation === true ? "ThumbUpIconCustom" : "ThumbsUp"}
                  className={cn("h-4 w-4")}
                />
              </Button>
            </div>
          </ShadTooltip>

          <ShadTooltip styleClasses="z-50" content={t("chat.message.notHelpful")} side="top">
            <div className="p-1">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => handleEvaluate(false)}
                className="h-8 w-8"
                data-testid="not-helpful-button"
              >
                <IconComponent
                  name={
                    evaluation === false ? "ThumbDownIconCustom" : "ThumbsDown"
                  }
                  className={cn("h-4 w-4")}
                />
              </Button>
            </div>
          </ShadTooltip>
        </div>
      )}
    </div>
  );
}