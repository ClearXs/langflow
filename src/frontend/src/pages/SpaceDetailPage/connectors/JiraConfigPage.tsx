import { Ticket } from "lucide-react";
import ApiKeyConnectorPage from "./ApiKeyConnectorPage";

export default function JiraConfigPage() {
  return (
    <ApiKeyConnectorPage
      config={{
        connectorType: "jira-connector",
        icon: <Ticket className="h-6 w-6" />,
        translationKey: "jira",
        apiKeyLabel: "Jira API Token",
        apiKeyPlaceholder: "your-api-token",
        apiKeyField: "JIRA_API_TOKEN",
        additionalFields: [
          {
            name: "jira_url",
            label: "Jira URL",
            placeholder: "https://your-domain.atlassian.net",
            configKey: "JIRA_URL",
            required: true,
          },
          {
            name: "email",
            label: "Email",
            placeholder: "your-email@example.com",
            configKey: "EMAIL",
            required: true,
          },
        ],
        features: ["issues", "projects", "sprints", "reports"],
      }}
    />
  );
}
