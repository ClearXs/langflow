import { Calendar } from "lucide-react";
import ApiKeyConnectorPage from "./ApiKeyConnectorPage";

export default function GoogleCalendarConfigPage() {
  return (
    <ApiKeyConnectorPage
      config={{
        connectorType: "google-calendar-connector",
        icon: <Calendar className="h-6 w-6" />,
        translationKey: "google_calendar",
        apiKeyLabel: "Google Calendar Credentials (JSON)",
        apiKeyPlaceholder: "Paste your credentials JSON here",
        apiKeyField: "GOOGLE_CREDENTIALS",
        features: ["events", "sync", "realtime", "collaborative"],
      }}
    />
  );
}
