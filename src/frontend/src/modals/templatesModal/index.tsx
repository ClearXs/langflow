import { useState } from "react";
import { useParams } from "react-router-dom";
import ForwardedIconComponent from "@/components/common/genericIconComponent";
import { Button } from "@/components/ui/button";
import { SidebarProvider } from "@/components/ui/sidebar";
import { useCustomNavigate } from "@/customization/hooks/use-custom-navigate";
import { track } from "@/customization/utils/analytics";
import useAddFlow from "@/hooks/flows/use-add-flow";
import type { Category } from "@/types/templates/types";
import type { newFlowModalPropsType } from "../../types/components";
import BaseModal from "../baseModal";
import GetStartedComponent from "./components/GetStartedComponent";
import { Nav } from "./components/navComponent";
import TemplateContentComponent from "./components/TemplateContentComponent";
import { useTranslation } from "react-i18next";

export default function TemplatesModal({
  open,
  setOpen,
}: newFlowModalPropsType): JSX.Element {
  const [currentTab, setCurrentTab] = useState("get-started");
  const addFlow = useAddFlow();
  const navigate = useCustomNavigate();
  const { folderId } = useParams();
  const { t } = useTranslation();
  // Define categories and their items
  const categories: Category[] = [
    {
      title: t("common.templates"),
      items: [
        { title: t("common.getStarted"), icon: "SquarePlay", id: "get-started" },
        { title: t("common.allTemplates"), icon: "LayoutPanelTop", id: "all-templates" },
      ],
    },
    {
      title: t("common.useCases"),
      items: [
        { title: t("common.assistants"), icon: "BotMessageSquare", id: "assistants" },
        { title: t("common.classification"), icon: "Tags", id: "classification" },
        { title: t("common.coding"), icon: "TerminalIcon", id: "coding" },
        {
          title: t("common.contentGeneration"),
          icon: "Newspaper",
          id: "content-generation",
        },
        { title: t("common.qA"), icon: "Database", id: "q-a" },
        // { title: t("common.summarization"), icon: "Bot", id: "summarization" },
        // { title: t("common.webScraping"), icon: "CodeXml", id: "web-scraping" },
      ],
    },
    {
      title: t("common.methodology"),
      items: [
        { title: t("common.prompting"), icon: "MessagesSquare", id: "chatbots" },
        { title: t("common.rag"), icon: "Database", id: "rag" },
        { title: t("common.agents"), icon: "Bot", id: "agents" },
      ],
    },
  ];

  return (
    <BaseModal size="templates" open={open} setOpen={setOpen} className="p-0">
      <BaseModal.Content className="flex flex-col p-0">
        <div className="flex h-full">
          <SidebarProvider width="15rem" defaultOpen={false}>
            <Nav
              categories={categories}
              currentTab={currentTab}
              setCurrentTab={setCurrentTab}
            />
            <main className="flex flex-1 flex-col gap-4 overflow-auto p-6 md:gap-8">
              {currentTab === "get-started" ? (
                <GetStartedComponent />
              ) : (
                <TemplateContentComponent
                  currentTab={currentTab}
                  categories={categories.flatMap((category) => category.items)}
                />
              )}
              <BaseModal.Footer>
                <div className="flex w-full flex-col justify-between gap-4 pb-4 sm:flex-row sm:items-center">
                  <div className="flex flex-col items-start justify-center">
                    <div className="font-semibold">{t("common.startFromScratch")}</div>
                    <div className="text-sm text-muted-foreground">
                      {t("common.beginWithAFreshFlowToBuildFromScratch")}
                    </div>
                  </div>
                  <Button
                    onClick={() => {
                      addFlow().then((id) => {
                        navigate(
                          `/flow/${id}${folderId ? `/folder/${folderId}` : ""}`,
                        );
                      });
                      track("New Flow Created", { template: "Blank Flow" });
                    }}
                    size="sm"
                    data-testid="blank-flow"
                    className="shrink-0"
                  >
                    <ForwardedIconComponent
                      name="Plus"
                      className="h-4 w-4 shrink-0"
                    />
                    {t("common.blankFlow")}
                  </Button>
                </div>
              </BaseModal.Footer>
            </main>
          </SidebarProvider>
        </div>
      </BaseModal.Content>
    </BaseModal>
  );
}
