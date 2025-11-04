import { useTranslation } from "react-i18next";
import IconComponent from "@/components/common/genericIconComponent";
import { Button } from "@/components/ui/button";
import { usePostMessageContext } from "@/contexts/postMessageContext";

export default function BackButton() {
  const { t } = useTranslation();

  const postMessageContext = usePostMessageContext();

  return (
    <Button
      variant="ghost"
      size="md"
      className="!px-2.5 font-normal"
      data-testid="publish-button"
      onClick={() => {
        setTimeout(() => {
          postMessageContext.sendToParent("close");
        }, 500);
      }}
    >
      <IconComponent name="SquareArrowLeft" className="!h-5 !w-5" />
      {t("flow.back")}
    </Button>
  );
}
