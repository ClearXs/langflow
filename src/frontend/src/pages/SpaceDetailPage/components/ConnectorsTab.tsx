import {
  Calendar,
  FileText,
  Github,
  Mail,
  MessageSquare,
  Plug,
  Table,
} from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ConnectorConfigDialog } from "./ConnectorConfigDialog";

interface ConnectorsTabProps {
  spaceId: number;
  onSuccess?: () => void;
}

interface ConnectorType {
  id: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  category: string;
  comingSoon?: boolean;
}

export function ConnectorsTab({ spaceId, onSuccess }: ConnectorsTabProps) {
  const { t } = useTranslation();
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const [selectedConnector, setSelectedConnector] = useState<ConnectorType | null>(null);

  const CONNECTOR_TYPES: ConnectorType[] = [
    // Messaging & Collaboration
    {
      id: "slack",
      name: "Slack",
      description: t("spaces.documents.connectors.types.slack.description"),
      icon: <MessageSquare className="h-5 w-5" />,
      category: "messaging",
    },
    {
      id: "discord",
      name: "Discord",
      description: t("spaces.documents.connectors.types.discord.description"),
      icon: <MessageSquare className="h-5 w-5" />,
      category: "messaging",
    },
    {
      id: "gmail",
      name: "Gmail",
      description: t("spaces.documents.connectors.types.gmail.description"),
      icon: <Mail className="h-5 w-5" />,
      category: "messaging",
    },

    // Documentation & Knowledge
    {
      id: "notion",
      name: "Notion",
      description: t("spaces.documents.connectors.types.notion.description"),
      icon: <FileText className="h-5 w-5" />,
      category: "knowledge",
    },
    {
      id: "confluence",
      name: "Confluence",
      description: t("spaces.documents.connectors.types.confluence.description"),
      icon: <FileText className="h-5 w-5" />,
      category: "knowledge",
    },

    // Development
    {
      id: "github",
      name: "GitHub",
      description: t("spaces.documents.connectors.types.github.description"),
      icon: <Github className="h-5 w-5" />,
      category: "development",
    },

    // Productivity
    {
      id: "google_calendar",
      name: "Google Calendar",
      description: t("spaces.documents.connectors.types.google_calendar.description"),
      icon: <Calendar className="h-5 w-5" />,
      category: "productivity",
    },
    {
      id: "airtable",
      name: "Airtable",
      description: t("spaces.documents.connectors.types.airtable.description"),
      icon: <Table className="h-5 w-5" />,
      category: "productivity",
    },
  ];

  const CATEGORIES = {
    messaging: t("spaces.documents.connectors.categories.messaging"),
    knowledge: t("spaces.documents.connectors.categories.knowledge"),
    development: t("spaces.documents.connectors.categories.development"),
    productivity: t("spaces.documents.connectors.categories.productivity"),
  };

  const filteredConnectors = CONNECTOR_TYPES.filter((connector) => {
    const matchesCategory =
      selectedCategory === "all" || connector.category === selectedCategory;
    const matchesSearch =
      searchQuery === "" ||
      connector.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      connector.description.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const handleConnectorClick = (connectorId: string) => {
    const connector = CONNECTOR_TYPES.find(c => c.id === connectorId);
    if (connector) {
      setSelectedConnector(connector);
      setConfigDialogOpen(true);
    }
  };

  return (
    <div className="space-y-6">
      {/* Icon and Description */}
      <div className="flex flex-col items-center text-center space-y-3">
        <div className="rounded-full bg-purple-100 dark:bg-purple-900/20 p-4">
          <Plug className="h-8 w-8 text-purple-600 dark:text-purple-400" />
        </div>
        <div className="space-y-1">
          <h3 className="text-lg font-semibold">
            {t("spaces.documents.connectors.title")}
          </h3>
          <p className="text-sm text-muted-foreground max-w-md">
            {t("spaces.documents.connectors.description")}
          </p>
        </div>
      </div>

      {/* Search and Filter */}
      <div className="flex flex-col sm:flex-row gap-3">
        <Input
          placeholder={t("spaces.documents.connectors.search_placeholder")}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="flex-1"
        />
        <Select value={selectedCategory} onValueChange={setSelectedCategory}>
          <SelectTrigger className="w-full sm:w-[200px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">
              {t("spaces.documents.connectors.all_categories")}
            </SelectItem>
            {Object.entries(CATEGORIES).map(([key, label]) => (
              <SelectItem key={key} value={key}>
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Connectors Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {filteredConnectors.map((connector) => (
          <button
            key={connector.id}
            onClick={() => handleConnectorClick(connector.id)}
            className="relative flex items-start gap-3 p-4 rounded-lg border bg-card hover:bg-accent hover:border-primary transition-all text-left group"
          >
            <div className="rounded-lg bg-muted p-2 group-hover:bg-background transition-colors">
              {connector.icon}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <h4 className="font-medium text-sm">{connector.name}</h4>
                {connector.comingSoon && (
                  <Badge variant="secondary" className="text-xs">
                    {t("spaces.documents.coming_soon")}
                  </Badge>
                )}
              </div>
              <p className="text-xs text-muted-foreground line-clamp-2">
                {connector.description}
              </p>
            </div>
          </button>
        ))}
      </div>

      {filteredConnectors.length === 0 && (
        <div className="text-center py-8">
          <p className="text-sm text-muted-foreground">
            {t("spaces.documents.connectors.no_results")}
          </p>
        </div>
      )}

      {/* Benefits Section */}
      <div className="rounded-lg border bg-muted/30 p-4 space-y-3">
        <p className="text-sm font-medium">
          {t("spaces.documents.connectors.benefits_title")}
        </p>
        <ul className="text-sm text-muted-foreground space-y-2">
          <li className="flex items-start gap-2">
            <span className="text-primary mt-0.5">✓</span>
            <span>{t("spaces.documents.connectors.benefit_auto_sync")}</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-primary mt-0.5">✓</span>
            <span>{t("spaces.documents.connectors.benefit_incremental")}</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-primary mt-0.5">✓</span>
            <span>{t("spaces.documents.connectors.benefit_unified")}</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-primary mt-0.5">✓</span>
            <span>{t("spaces.documents.connectors.benefit_realtime")}</span>
          </li>
        </ul>
      </div>

      {/* Connector Configuration Dialog */}
      {selectedConnector && (
        <ConnectorConfigDialog
          open={configDialogOpen}
          onOpenChange={setConfigDialogOpen}
          connectorId={selectedConnector.id}
          connectorName={selectedConnector.name}
          connectorIcon={selectedConnector.icon}
          spaceId={spaceId}
          onSuccess={onSuccess}
        />
      )}
    </div>
  );
}
