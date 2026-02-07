import { Table } from "lucide-react";
import ApiKeyConnectorPage from "./ApiKeyConnectorPage";

export default function AirtableConfigPage() {
  return (
    <ApiKeyConnectorPage
      config={{
        connectorType: "airtable-connector",
        icon: <Table className="h-6 w-6" />,
        translationKey: "airtable",
        apiKeyLabel: "Airtable API Key",
        apiKeyPlaceholder: "pat...xxxxxxxxxxxxx",
        apiKeyField: "AIRTABLE_API_KEY",
        additionalFields: [
          {
            name: "base_id",
            label: "Base ID",
            placeholder: "appXXXXXXXXXXXXXX",
            configKey: "BASE_ID",
            required: false,
          },
        ],
        features: ["flexible", "collaborative", "visual", "powerful"],
      }}
    />
  );
}
