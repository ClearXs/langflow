import { BookOpen } from "lucide-react";
import ApiKeyConnectorPage from "./ApiKeyConnectorPage";

export default function NotionConfigPage() {
  return (
    <ApiKeyConnectorPage
      config={{
        connectorType: "notion-connector",
        icon: <BookOpen className="h-6 w-6" />,
        translationKey: "notion",
        apiKeyLabel: "Notion Integration Token",
        apiKeyPlaceholder: "secret_xxxxxxxxxxxxx",
        apiKeyField: "NOTION_TOKEN",
        features: ["pages", "databases", "collaborative", "flexible"],
      }}
    />
  );
}
