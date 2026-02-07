import { ArrowLeft } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { ConnectorsTab } from "@/components/sources/ConnectorsTab";
import { Button } from "@/components/ui/button";

export default function SourcesAddPage() {
  const { t } = useTranslation();
  const { spaceId } = useParams<{ spaceId: string }>();
  const navigate = useNavigate();

  const handleBack = () => {
    navigate(`/spaces/${spaceId}/connectors`);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b px-6 py-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={handleBack}
              className="h-8 w-8"
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <div>
              <h2 className="text-lg font-semibold">
                {t("connectors.manage.add_connector")}
              </h2>
              <p className="text-sm text-muted-foreground">
                {t("connectors.manage.subtitle")}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        {spaceId && <ConnectorsTab searchSpaceId={spaceId} />}
      </div>
    </div>
  );
}
