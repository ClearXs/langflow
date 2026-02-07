import { Plug, Plus } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";

export default function ConnectorsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { spaceId } = useParams<{ spaceId: string }>();

  const handleAddConnector = () => {
    navigate(`/spaces/${spaceId}/sources/add?tab=connectors`);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Connectors Header */}
      <div className="border-b px-6 py-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold">
              {t("spaces.connectors.title")}
            </h2>
            <p className="text-sm text-muted-foreground">
              {t("spaces.connectors.subtitle")}
            </p>
          </div>
          <Button onClick={handleAddConnector}>
            <Plus className="mr-2 h-4 w-4" />
            {t("spaces.connectors.addConnector")}
          </Button>
        </div>
      </div>

      {/* Connectors Content */}
      <div className="flex-1 overflow-auto p-6">
        {/* Empty State */}
        <div className="h-full flex flex-col items-center justify-center py-20 px-8">
          <div className="rounded-full bg-muted p-6 mb-6">
            <Plug className="h-12 w-12 text-muted-foreground" />
          </div>
          <h3 className="text-xl font-semibold mb-3">
            {t("spaces.connectors.noConnectorsYet")}
          </h3>
          <p className="text-muted-foreground text-center max-w-md mb-8 text-base">
            {t("spaces.connectors.emptyStateDescription")}
          </p>
          <Button onClick={handleAddConnector} size="lg">
            <Plus className="mr-2 h-5 w-5" />
            {t("spaces.connectors.addYourFirstConnector")}
          </Button>
        </div>
      </div>
    </div>
  );
}
