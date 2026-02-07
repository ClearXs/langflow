import { MessageCircle } from "lucide-react";
import ApiKeyConnectorPage from "./ApiKeyConnectorPage";

export default function DiscordConfigPage() {
  return (
    <ApiKeyConnectorPage
      config={{
        connectorType: "discord-connector",
        icon: <MessageCircle className="h-6 w-6" />,
        translationKey: "discord",
        apiKeyLabel: "Discord Bot Token",
        apiKeyPlaceholder: "MTxxxxxxxxx.xxxxxx.xxxxxxxxxxxxxxxxxxxxxxxxxxx",
        apiKeyField: "DISCORD_BOT_TOKEN",
        additionalFields: [
          {
            name: "guild_id",
            label: "Server (Guild) ID (Optional)",
            placeholder: "123456789012345678",
            configKey: "GUILD_ID",
            required: false,
          },
        ],
        features: ["servers", "channels", "messages", "realtime"],
      }}
    />
  );
}
