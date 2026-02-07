import { Search } from "lucide-react";
import ApiKeyConnectorPage from "./ApiKeyConnectorPage";

export default function BaiduConfigPage() {
  return (
    <ApiKeyConnectorPage
      config={{
        connectorType: "baidu-search-api",
        icon: <Search className="h-6 w-6" />,
        translationKey: "baidu",
        apiKeyLabel: "Baidu API Key",
        apiKeyPlaceholder: "baidu_xxxxxxxxxxxxx",
        apiKeyField: "BAIDU_API_KEY",
        features: ["search", "chinese", "local", "comprehensive"],
      }}
    />
  );
}
