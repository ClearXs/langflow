import { ArrowLeft } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

// Import all connector config pages
import AirtableConfigPage from "./connectors/AirtableConfigPage";
import BaiduConfigPage from "./connectors/BaiduConfigPage";
import BookStackConfigPage from "./connectors/BookStackConfigPage";
import ClickUpConfigPage from "./connectors/ClickUpConfigPage";
import ConfluenceConfigPage from "./connectors/ConfluenceConfigPage";
import DiscordConfigPage from "./connectors/DiscordConfigPage";
import ElasticsearchConfigPage from "./connectors/ElasticsearchConfigPage";
import GitHubConfigPage from "./connectors/GitHubConfigPage";
import GmailConfigPage from "./connectors/GmailConfigPage";
import GoogleCalendarConfigPage from "./connectors/GoogleCalendarConfigPage";
import JiraConfigPage from "./connectors/JiraConfigPage";
import LinearConfigPage from "./connectors/LinearConfigPage";
import LinkupConfigPage from "./connectors/LinkupConfigPage";
import LumaConfigPage from "./connectors/LumaConfigPage";
import NotionConfigPage from "./connectors/NotionConfigPage";
import SearxNGConfigPage from "./connectors/SearxNGConfigPage";
import SlackConfigPage from "./connectors/SlackConfigPage";
import TavilyConfigPage from "./connectors/TavilyConfigPage";
import WebCrawlerConfigPage from "./connectors/WebCrawlerConfigPage";

export default function ConnectorConfigPage() {
  const { connectorId } = useParams<{ connectorId: string }>();

  // Route to specific connector config page based on connectorId
  switch (connectorId) {
    // Web Crawling
    case "webcrawler-connector":
      return <WebCrawlerConfigPage />;

    // Web Search
    case "tavily-api":
      return <TavilyConfigPage />;
    case "searxng":
      return <SearxNGConfigPage />;
    case "linkup-api":
      return <LinkupConfigPage />;
    case "baidu-search-api":
      return <BaiduConfigPage />;

    // Messaging
    case "slack-connector":
      return <SlackConfigPage />;
    case "discord-connector":
      return <DiscordConfigPage />;

    // Project Management
    case "linear-connector":
      return <LinearConfigPage />;
    case "jira-connector":
      return <JiraConfigPage />;
    case "clickup-connector":
      return <ClickUpConfigPage />;

    // Documentation
    case "notion-connector":
      return <NotionConfigPage />;
    case "confluence-connector":
      return <ConfluenceConfigPage />;
    case "bookstack-connector":
      return <BookStackConfigPage />;

    // Development
    case "github-connector":
      return <GitHubConfigPage />;

    // Databases
    case "elasticsearch-connector":
      return <ElasticsearchConfigPage />;
    case "airtable-connector":
      return <AirtableConfigPage />;

    // Productivity
    case "google-calendar-connector":
      return <GoogleCalendarConfigPage />;
    case "google-gmail-connector":
      return <GmailConfigPage />;
    case "luma-connector":
      return <LumaConfigPage />;

    default:
      // Fallback to generic placeholder
      return <GenericConnectorConfigPage connectorId={connectorId} />;
  }
}

// Generic placeholder for connectors not yet implemented
function GenericConnectorConfigPage({ connectorId }: { connectorId?: string }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { spaceId } = useParams<{ spaceId: string }>();

  const handleGoBack = () => {
    navigate(`/spaces/${spaceId}/sources/add?tab=connectors`);
  };

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="mb-6">
        <Button variant="ghost" onClick={handleGoBack} className="mb-4">
          <ArrowLeft className="mr-2 h-4 w-4" />
          {t("common.back")}
        </Button>

        <h1 className="text-3xl font-bold">{t("connectors.config.title")}</h1>
        <p className="text-muted-foreground mt-2">
          {t("connectors.config.subtitle")}
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t("connectors.config.configure")}</CardTitle>
          <CardDescription>
            {t("connectors.config.configure_desc", {
              connector: connectorId,
            })}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="rounded-lg border border-dashed border-gray-300 dark:border-gray-700 p-8 text-center">
              <p className="text-sm text-muted-foreground">
                {t("connectors.config.coming_soon")}
              </p>
              <p className="text-xs text-muted-foreground mt-2">
                {t("connectors.config.coming_soon_desc")}
              </p>
            </div>

            <div className="flex justify-end gap-2 pt-4">
              <Button variant="outline" onClick={handleGoBack}>
                {t("common.cancel")}
              </Button>
              <Button disabled>{t("common.save")}</Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
