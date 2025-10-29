import { useTranslation } from "react-i18next";
import { Outlet, type To } from "react-router-dom";
import SideBarButtonsComponent from "@/components/core/sidebarComponent";
import { SidebarProvider } from "@/components/ui/sidebar";
import { CustomStoreSidebar } from "@/customization/components/custom-store-sidebar";
import {
  ENABLE_DATASTAX_LANGFLOW,
  ENABLE_LANGFLOW_STORE,
  ENABLE_PROFILE_ICONS,
} from "@/customization/feature-flags";
import { useIsEmbedded } from "@/hooks/use-iframe-params";
import useAuthStore from "@/stores/authStore";
import { useStoreStore } from "@/stores/storeStore";
import ForwardedIconComponent from "../../components/common/genericIconComponent";
import PageLayout from "../../components/common/pageLayout";
export default function SettingsPage(): JSX.Element {
  const autoLogin = useAuthStore((state) => state.autoLogin);
  const hasStore = useStoreStore((state) => state.hasStore);
  const isEmbedded = useIsEmbedded();

  const { t } = useTranslation();

  // Hides the General settings if there is nothing to show
  const showGeneralSettings = ENABLE_PROFILE_ICONS || hasStore || !autoLogin;

  const sidebarNavItems: {
    href?: string;
    title: string;
    icon: React.ReactNode;
  }[] = [];

  // Hide General, MCP Servers, and Langflow API Keys when embedded
  if (showGeneralSettings && !isEmbedded) {
    sidebarNavItems.push({
      title: t("settings.general"),
      href: "/settings/general",
      icon: (
        <ForwardedIconComponent
          name="SlidersHorizontal"
          className="w-4 flex-shrink-0 justify-start stroke-[1.5]"
        />
      ),
    });
  }

  if (!isEmbedded) {
    sidebarNavItems.push({
      title: t("settings.mcpServers"),
      href: "/settings/mcp-servers",
      icon: (
        <ForwardedIconComponent
          name="Mcp"
          className="w-4 flex-shrink-0 justify-start stroke-[1.5]"
        />
      ),
    });
  }

  sidebarNavItems.push(
    {
      title: t("dataSource.management"),
      href: "/settings/datasources",
      icon: (
        <ForwardedIconComponent
          name="Database"
          className="w-4 flex-shrink-0 justify-start stroke-[1.5]"
        />
      ),
    },
    {
      title: t("settings.globalVariables"),
      href: "/settings/global-variables",
      icon: (
        <ForwardedIconComponent
          name="Globe"
          className="w-4 flex-shrink-0 justify-start stroke-[1.5]"
        />
      ),
    },

    {
      title: t("settings.shortcuts"),
      href: "/settings/shortcuts",
      icon: (
        <ForwardedIconComponent
          name="Keyboard"
          className="w-4 flex-shrink-0 justify-start stroke-[1.5]"
        />
      ),
    },
    {
      title: t("settings.messages"),
      href: "/settings/messages",
      icon: (
        <ForwardedIconComponent
          name="MessagesSquare"
          className="w-4 flex-shrink-0 justify-start stroke-[1.5]"
        />
      ),
    },
  );

  // TODO: Remove this on cleanup
  // Hide Langflow API Keys when embedded
  if (!ENABLE_DATASTAX_LANGFLOW) {
    const langflowItems = CustomStoreSidebar(
      !isEmbedded,
      ENABLE_LANGFLOW_STORE,
    );
    sidebarNavItems.splice(2, 0, ...langflowItems);
  }

  return (
    <PageLayout
      backTo={-1 as To}
      title={t("settings.displayName")}
      description={t("settings.description")}
    >
      <SidebarProvider width="15rem" defaultOpen={false}>
        <SideBarButtonsComponent items={sidebarNavItems} />
        <main className="flex flex-1 overflow-hidden">
          <div className="flex flex-1 flex-col overflow-x-hidden pt-1">
            <Outlet />
          </div>
        </main>
      </SidebarProvider>
    </PageLayout>
  );
}
