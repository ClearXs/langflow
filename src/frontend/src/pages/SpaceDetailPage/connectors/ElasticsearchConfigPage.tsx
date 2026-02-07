import { Database } from "lucide-react";
import ApiKeyConnectorPage from "./ApiKeyConnectorPage";

export default function ElasticsearchConfigPage() {
  return (
    <ApiKeyConnectorPage
      config={{
        connectorType: "elasticsearch-connector",
        icon: <Database className="h-6 w-6" />,
        translationKey: "elasticsearch",
        apiKeyLabel: "Elasticsearch URL",
        apiKeyPlaceholder: "https://elasticsearch.example.com:9200",
        apiKeyField: "ELASTICSEARCH_URL",
        additionalFields: [
          {
            name: "index_name",
            label: "Index Name",
            placeholder: "my-index",
            configKey: "INDEX_NAME",
            required: false,
          },
          {
            name: "username",
            label: "Username (Optional)",
            placeholder: "elastic",
            configKey: "USERNAME",
            required: false,
          },
          {
            name: "password",
            label: "Password (Optional)",
            placeholder: "••••••••",
            configKey: "PASSWORD",
            required: false,
          },
        ],
        features: ["scalable", "realtime", "distributed", "powerful"],
      }}
    />
  );
}
