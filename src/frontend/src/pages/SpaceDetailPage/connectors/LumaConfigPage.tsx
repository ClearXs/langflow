import { Sparkles } from "lucide-react";
import ApiKeyConnectorPage from "./ApiKeyConnectorPage";

export default function LumaConfigPage() {
  return (
    <ApiKeyConnectorPage
      config={{
        connectorType: "luma-connector",
        icon: <Sparkles className="h-6 w-6" />,
        translationKey: "luma",
        apiKeyLabel: "Luma API Key",
        apiKeyPlaceholder: "luma_xxxxxxxxxxxxx",
        apiKeyField: "LUMA_API_KEY",
        features: ["events", "calendar", "sync", "realtime"],
      }}
    />
  );
}
