import { Book } from "lucide-react";
import ApiKeyConnectorPage from "./ApiKeyConnectorPage";

export default function ConfluenceConfigPage() {
  return (
    <ApiKeyConnectorPage
      config={{
        connectorType: "confluence-connector",
        icon: <Book className="h-6 w-6" />,
        translationKey: "confluence",
        apiKeyLabel: "Confluence API Token",
        apiKeyPlaceholder: "your-api-token",
        apiKeyField: "CONFLUENCE_API_TOKEN",
        additionalFields: [
          {
            name: "confluence_url",
            label: "Confluence URL",
            placeholder: "https://your-domain.atlassian.net/wiki",
            configKey: "CONFLUENCE_URL",
            required: true,
          },
          {
            name: "email",
            label: "Email",
            placeholder: "your-email@example.com",
            configKey: "EMAIL",
            required: true,
          },
        ],
        features: ["spaces", "pages", "collaborative", "knowledge"],
      }}
    />
  );
}
