import { FileText, Globe, Plug, Youtube } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ConnectorsTab } from "./ConnectorsTab";
import { UploadDocumentsTab } from "./UploadDocumentsTab";
import { WebPagesTab } from "./WebPagesTab";
import { YouTubeTab } from "./YouTubeTab";

interface AddDataSourcesDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  spaceId: number;
  onUploadSuccess?: () => void;
}

export function AddDataSourcesDialog({
  open,
  onOpenChange,
  spaceId,
  onUploadSuccess,
}: AddDataSourcesDialogProps) {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState("documents");

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[700px] max-h-[85vh]">
        <DialogHeader>
          <DialogTitle>{t("spaces.documents.add_sources")}</DialogTitle>
          <DialogDescription>
            {t("spaces.documents.add_sources_description")}
          </DialogDescription>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="documents" className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              <span className="hidden sm:inline">
                {t("spaces.documents.tabs.documents")}
              </span>
            </TabsTrigger>
            <TabsTrigger value="youtube" className="flex items-center gap-2">
              <Youtube className="h-4 w-4" />
              <span className="hidden sm:inline">
                {t("spaces.documents.tabs.youtube")}
              </span>
            </TabsTrigger>
            <TabsTrigger value="web" className="flex items-center gap-2">
              <Globe className="h-4 w-4" />
              <span className="hidden sm:inline">
                {t("spaces.documents.tabs.web_pages")}
              </span>
            </TabsTrigger>
            <TabsTrigger value="connectors" className="flex items-center gap-2">
              <Plug className="h-4 w-4" />
              <span className="hidden sm:inline">
                {t("spaces.documents.tabs.connectors")}
              </span>
            </TabsTrigger>
          </TabsList>

          <div className="mt-6 overflow-y-auto max-h-[calc(85vh-200px)]">
            <TabsContent value="documents" className="mt-0">
              <UploadDocumentsTab
                spaceId={spaceId}
                onUploadSuccess={() => {
                  onUploadSuccess?.();
                  onOpenChange(false);
                }}
              />
            </TabsContent>

            <TabsContent value="youtube" className="mt-0">
              <YouTubeTab
                spaceId={spaceId}
                onSuccess={() => {
                  onUploadSuccess?.();
                  onOpenChange(false);
                }}
              />
            </TabsContent>

            <TabsContent value="web" className="mt-0">
              <WebPagesTab
                spaceId={spaceId}
                onSuccess={() => {
                  onUploadSuccess?.();
                  onOpenChange(false);
                }}
              />
            </TabsContent>

            <TabsContent value="connectors" className="mt-0">
              <ConnectorsTab
                spaceId={spaceId}
                onSuccess={() => {
                  onUploadSuccess?.();
                  onOpenChange(false);
                }}
              />
            </TabsContent>
          </div>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
