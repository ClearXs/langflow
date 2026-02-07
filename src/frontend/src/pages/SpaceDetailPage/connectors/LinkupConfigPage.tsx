import { Link } from "lucide-react";
import ApiKeyConnectorPage from "./ApiKeyConnectorPage";

export default function LinkupConfigPage() {
  return (
    <ApiKeyConnectorPage
      config={{
        connectorType: "linkup-api",
        icon: <Link className="h-6 w-6" />,
        translationKey: "linkup",
        apiKeyLabel: "Linkup API Key",
        apiKeyPlaceholder: "linkup_xxxxxxxxxxxxx",
        apiKeyField: "LINKUP_API_KEY",
        features: ["advanced", "search", "fast", "reliable"],
      }}
    />
  );
}
