import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import useFlowStore from "@/stores/flowStore";
import { cn } from "@/utils/utils";
import { useGetReplacementComponents } from "../../hooks/use-get-replacement-components";

export default function NodeLegacyComponent({
  legacy,
  replacement,
  setDismissAll,
}: {
  legacy?: boolean;
  replacement?: string[];
  setDismissAll: (value: boolean) => void;
}) {
  const { t } = useTranslation();
  
  const setFilterComponent = useFlowStore((state) => state.setFilterComponent);
  const setFilterType = useFlowStore((state) => state.setFilterType);
  const setFilterEdge = useFlowStore((state) => state.setFilterEdge);

  const handleFilterComponent = (component: string) => {
    setFilterComponent(component);
    setFilterType(undefined);
    setFilterEdge([]);
  };

  const foundComponents = useGetReplacementComponents(replacement);

  return (
    <div
      className={cn(
        "flex w-full flex-col items-center gap-3 rounded-t-[0.69rem] border-b bg-muted p-2 px-4 py-2",
      )}
    >
      <div className="flex w-full items-center gap-3">
        <div className="h-2.5 w-2.5 rounded-full bg-warning" />
        <div className="mb-px flex-1 truncate text-mmd font-medium">
          {t("components.nodeLegacy.legacy")}
        </div>

        <Button
          variant="ghost"
          size="icon"
          className="shrink-0 !text-mmd"
          onClick={(e) => {
            e.stopPropagation();
            setDismissAll(true);
          }}
          aria-label={t("components.nodeLegacy.dismissWarningBar")}
          data-testid="dismiss-warning-bar"
        >
          {t("components.nodeLegacy.dismiss")}
        </Button>
      </div>
      <div className="w-full text-mmd text-muted-foreground">
        {replacement &&
        Array.isArray(replacement) &&
        replacement.length > 0 &&
        foundComponents.some((component) => component) ? (
          <span className="block items-center">
            {t("components.nodeLegacy.use")}{" "}
            {foundComponents.map((component, index) => (
              <>
                {component && (
                  <>
                    {index > 0 && ", "}
                    <Button
                      variant="link"
                      className="!inline-block !text-mmd !text-accent-pink-foreground"
                      size={null}
                      onClick={() => handleFilterComponent(replacement[index])}
                    >
                      <span>{component}</span>
                    </Button>
                  </>
                )}
              </>
            ))}
            .
          </span>
        ) : (
          t("components.nodeLegacy.noDirectReplacement")
        )}
      </div>
    </div>
  );
}