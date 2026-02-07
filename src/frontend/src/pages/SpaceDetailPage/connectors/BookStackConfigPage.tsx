import { Book } from "lucide-react";
import ApiKeyConnectorPage from "./ApiKeyConnectorPage";

export default function BookStackConfigPage() {
  return (
    <ApiKeyConnectorPage
      config={{
        connectorType: "bookstack-connector",
        icon: <Book className="h-6 w-6" />,
        translationKey: "bookstack",
        apiKeyLabel: "BookStack API Token",
        apiKeyPlaceholder: "your-api-token",
        apiKeyField: "BOOKSTACK_API_TOKEN",
        additionalFields: [
          {
            name: "bookstack_url",
            label: "BookStack URL",
            placeholder: "https://bookstack.example.com",
            configKey: "BOOKSTACK_URL",
            required: true,
          },
          {
            name: "token_id",
            label: "Token ID",
            placeholder: "your-token-id",
            configKey: "TOKEN_ID",
            required: true,
          },
        ],
        features: ["books", "chapters", "pages", "wiki"],
      }}
    />
  );
}
