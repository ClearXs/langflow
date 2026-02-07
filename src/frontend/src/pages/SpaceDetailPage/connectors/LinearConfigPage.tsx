import { Kanban } from "lucide-react";
import ApiKeyConnectorPage from "./ApiKeyConnectorPage";

export default function LinearConfigPage() {
  return (
    <ApiKeyConnectorPage
      config={{
        connectorType: "linear-connector",
        icon: <Kanban className="h-6 w-6" />,
        translationKey: "linear",
        apiKeyLabel: "Linear API Key",
        apiKeyPlaceholder: "lin_api_xxxxxxxxxxxxx",
        apiKeyField: "LINEAR_API_KEY",
        features: ["issues", "projects", "roadmaps", "sync"],
      }}
    />
  );
}
