import {
  FileText,
  MessageSquare,
  Plug,
  Settings,
  Users,
} from "lucide-react";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Link, Outlet, useParams } from "react-router-dom";
import SideBarFoldersButtonsComponent from "@/components/core/folderSidebarComponent/components/sideBarFolderButtons";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { SidebarProvider, useSidebar } from "@/components/ui/sidebar";
import { useGetSpaceQuery } from "@/controllers/API/queries/spaces";
import { useCustomNavigate } from "@/customization/hooks/use-custom-navigate";
import useSpacesStore from "@/stores/spacesStore";
import { cn } from "@/utils/utils";

// Navigation items configuration with i18n keys
const navigationItemsConfig = [
  {
    i18nKey: "navigation.chats",
    href: "chats",
    icon: MessageSquare,
  },
  {
    i18nKey: "navigation.notes",
    href: "notes",
    icon: FileText,
  },
  {
    i18nKey: "navigation.documents",
    href: "documents",
    icon: FileText,
  },
  {
    i18nKey: "navigation.connectors",
    href: "connectors",
    icon: Plug,
  },
  {
    i18nKey: "navigation.team",
    href: "team",
    icon: Users,
  },
  {
    i18nKey: "common.settings",
    href: "settings",
    icon: Settings,
  },
];

// Inner component that can use useSidebar hook
function SpaceContent({
  space,
  spaceId,
}: {
  space: any;
  spaceId: string | undefined;
}) {
  const { t } = useTranslation();
  const { state } = useSidebar();

  return (
    <div className="flex h-full w-full">
      {/* 空间导航侧边栏 / Space navigation sidebar */}
      {/* Only show when main sidebar is expanded */}
      {state === "expanded" && (
        <aside className="w-64 border-r bg-muted/10 flex flex-col">
          {/* Space Header */}
          <div className="p-6 border-b">
            <h2 className="text-lg font-semibold line-clamp-2">{space.name}</h2>
            {space.description && (
              <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                {space.description}
              </p>
            )}
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4">
            <ul className="space-y-1">
              {navigationItemsConfig.map((item) => {
                const isActive = window.location.pathname.includes(item.href);
                return (
                  <li key={item.href}>
                    <Link
                      to={`/spaces/${spaceId}/${item.href}`}
                      className={cn(
                        "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                        isActive
                          ? "bg-primary text-primary-foreground"
                          : "hover:bg-muted text-muted-foreground hover:text-foreground",
                      )}
                    >
                      <item.icon className="h-4 w-4" />
                      {t(item.i18nKey)}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </nav>

          <Separator />
        </aside>
      )}

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}

export default function SpaceDetailLayout() {
  const { t } = useTranslation();
  const { spaceId } = useParams<{ spaceId: string }>();
  const setActiveSpaceId = useSpacesStore((state) => state.setActiveSpaceId);
  const navigate = useCustomNavigate();

  const { data: space, isLoading } = useGetSpaceQuery(
    { enabled: !!spaceId },
    { spaceId: Number(spaceId) },
  );

  useEffect(() => {
    if (spaceId) {
      setActiveSpaceId(Number(spaceId));
    }
  }, [spaceId, setActiveSpaceId]);

  return (
    <SidebarProvider width="280px">
      {/* 左侧分组导航侧边栏 / Left grouped navigation sidebar */}
      <SideBarFoldersButtonsComponent
        handleChangeFolder={(id: string) => {
          navigate(`all/folder/${id}`);
        }}
        handleDeleteFolder={() => {}}
        handleFilesClick={() => {
          navigate("assets");
        }}
      />

      {/* 主内容区域 / Main content area */}
      {isLoading ? (
        <div className="flex items-center justify-center h-screen w-full">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      ) : !space ? (
        <div className="flex flex-col items-center justify-center h-screen w-full">
          <h2 className="text-2xl font-bold mb-2">Space Not Found</h2>
          <p className="text-muted-foreground mb-4">
            The space you're looking for doesn't exist
          </p>
          <Link to="/spaces">
            <Button>Back to Spaces</Button>
          </Link>
        </div>
      ) : (
        <SpaceContent space={space} spaceId={spaceId} />
      )}
    </SidebarProvider>
  );
}
