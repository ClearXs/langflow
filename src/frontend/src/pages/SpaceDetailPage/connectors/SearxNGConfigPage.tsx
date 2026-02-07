import { Globe } from "lucide-react";
import ApiKeyConnectorPage from "./ApiKeyConnectorPage";

export default function SearxNGConfigPage() {
  return (
    <ApiKeyConnectorPage
      config={{
        connectorType: "searxng",
        icon: <Globe className="h-6 w-6" />,
        translationKey: "searxng",
        apiKeyLabel: "SearxNG Instance URL",
        apiKeyPlaceholder: "https://searx.example.com",
        apiKeyField: "SEARXNG_URL",
        features: ["private", "metasearch", "opensource", "customizable"],
      }}
    />
  );
}
