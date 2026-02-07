import { Globe } from "lucide-react";
import ApiKeyConnectorPage from "./ApiKeyConnectorPage";

export default function TavilyConfigPage() {
  return (
    <ApiKeyConnectorPage
      config={{
        connectorType: "tavily-api",
        icon: <Globe className="h-6 w-6" />,
        translationKey: "tavily",
        apiKeyLabel: "Tavily API Key",
        apiKeyPlaceholder: "tvly-xxxxxxxxxxxxx",
        apiKeyField: "TAVILY_API_KEY",
        features: ["search", "realtime", "fast", "reliable"],
      }}
    />
  );
}
