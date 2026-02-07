import { Mail } from "lucide-react";
import ApiKeyConnectorPage from "./ApiKeyConnectorPage";

export default function GmailConfigPage() {
  return (
    <ApiKeyConnectorPage
      config={{
        connectorType: "google-gmail-connector",
        icon: <Mail className="h-6 w-6" />,
        translationKey: "gmail",
        apiKeyLabel: "Gmail Credentials (JSON)",
        apiKeyPlaceholder: "Paste your credentials JSON here",
        apiKeyField: "GOOGLE_CREDENTIALS",
        features: ["emails", "labels", "search", "sync"],
      }}
    />
  );
}
