import {
  Book,
  BookOpen,
  Calendar,
  CheckSquare,
  Database,
  Globe,
  Kanban,
  Link,
  Mail,
  MessageCircle,
  Search,
  Sparkles,
  Table,
  Ticket,
} from "lucide-react";

export interface Connector {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  status: "available" | "coming-soon" | "connected";
}

export interface ConnectorCategory {
  id: string;
  title: string;
  connectors: Connector[];
}

export const connectorCategories: ConnectorCategory[] = [
  {
    id: "web-crawling",
    title: "web_crawling",
    connectors: [
      {
        id: "webcrawler-connector",
        title: "Web Pages",
        description: "webcrawler_desc",
        icon: <Globe className="h-6 w-6" />,
        status: "available",
      },
    ],
  },
  {
    id: "web-search",
    title: "web_search",
    connectors: [
      {
        id: "tavily-api",
        title: "Tavily API",
        description: "tavily_desc",
        icon: <Globe className="h-6 w-6" />,
        status: "available",
      },
      {
        id: "searxng",
        title: "SearxNG",
        description: "searxng_desc",
        icon: <Globe className="h-6 w-6" />,
        status: "available",
      },
      {
        id: "linkup-api",
        title: "Linkup API",
        description: "linkup_desc",
        icon: <Link className="h-6 w-6" />,
        status: "available",
      },
      {
        id: "baidu-search-api",
        title: "Baidu Search",
        description: "baidu_desc",
        icon: <Search className="h-6 w-6" />,
        status: "available",
      },
    ],
  },
  {
    id: "messaging",
    title: "messaging",
    connectors: [
      {
        id: "slack-connector",
        title: "Slack",
        description: "slack_desc",
        icon: <MessageCircle className="h-6 w-6" />,
        status: "available",
      },
      {
        id: "discord-connector",
        title: "Discord",
        description: "discord_desc",
        icon: <MessageCircle className="h-6 w-6" />,
        status: "available",
      },
    ],
  },
  {
    id: "project-management",
    title: "project_management",
    connectors: [
      {
        id: "linear-connector",
        title: "Linear",
        description: "linear_desc",
        icon: <Kanban className="h-6 w-6" />,
        status: "available",
      },
      {
        id: "jira-connector",
        title: "Jira",
        description: "jira_desc",
        icon: <Ticket className="h-6 w-6" />,
        status: "available",
      },
      {
        id: "clickup-connector",
        title: "ClickUp",
        description: "clickup_desc",
        icon: <CheckSquare className="h-6 w-6" />,
        status: "available",
      },
    ],
  },
  {
    id: "documentation",
    title: "documentation",
    connectors: [
      {
        id: "notion-connector",
        title: "Notion",
        description: "notion_desc",
        icon: <BookOpen className="h-6 w-6" />,
        status: "available",
      },
      {
        id: "confluence-connector",
        title: "Confluence",
        description: "confluence_desc",
        icon: <Book className="h-6 w-6" />,
        status: "available",
      },
      {
        id: "bookstack-connector",
        title: "BookStack",
        description: "bookstack_desc",
        icon: <Book className="h-6 w-6" />,
        status: "available",
      },
    ],
  },
  {
    id: "development",
    title: "development",
    connectors: [
      {
        id: "github-connector",
        title: "GitHub",
        description: "github_desc",
        icon: <Globe className="h-6 w-6" />,
        status: "available",
      },
    ],
  },
  {
    id: "databases",
    title: "databases",
    connectors: [
      {
        id: "elasticsearch-connector",
        title: "Elasticsearch",
        description: "elasticsearch_desc",
        icon: <Database className="h-6 w-6" />,
        status: "available",
      },
      {
        id: "airtable-connector",
        title: "Airtable",
        description: "airtable_desc",
        icon: <Table className="h-6 w-6" />,
        status: "available",
      },
    ],
  },
  {
    id: "productivity",
    title: "productivity",
    connectors: [
      {
        id: "google-calendar-connector",
        title: "Google Calendar",
        description: "calendar_desc",
        icon: <Calendar className="h-6 w-6" />,
        status: "available",
      },
      {
        id: "google-gmail-connector",
        title: "Gmail",
        description: "gmail_desc",
        icon: <Mail className="h-6 w-6" />,
        status: "available",
      },
      {
        id: "luma-connector",
        title: "Luma",
        description: "luma_desc",
        icon: <Sparkles className="h-6 w-6" />,
        status: "available",
      },
    ],
  },
];
