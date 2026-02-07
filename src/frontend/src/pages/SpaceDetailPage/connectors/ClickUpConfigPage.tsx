import { CheckSquare } from "lucide-react";
import ApiKeyConnectorPage from "./ApiKeyConnectorPage";

export default function ClickUpConfigPage() {
  return (
    <ApiKeyConnectorPage
      config={{
        connectorType: "clickup-connector",
        icon: <CheckSquare className="h-6 w-6" />,
        translationKey: "clickup",
        apiKeyLabel: "ClickUp API Token",
        apiKeyPlaceholder: "pk_xxxxxxxxxxxxx",
        apiKeyField: "CLICKUP_API_TOKEN",
        features: ["tasks", "spaces", "lists", "customizable"],
      }}
    />
  );
}
