import { MessageCircle } from "lucide-react";
import ApiKeyConnectorPage from "./ApiKeyConnectorPage";

export default function SlackConfigPage() {
  return (
    <ApiKeyConnectorPage
      config={{
        connectorType: "slack-connector",
        icon: <MessageCircle className="h-6 w-6" />,
        translationKey: "slack",
        apiKeyLabel: "Slack Bot Token",
        apiKeyPlaceholder: "xoxb-xxxxxxxxxxxxx",
        apiKeyField: "SLACK_BOT_TOKEN",
        features: ["channels", "messages", "realtime", "collaborative"],
      }}
    />
  );
}
