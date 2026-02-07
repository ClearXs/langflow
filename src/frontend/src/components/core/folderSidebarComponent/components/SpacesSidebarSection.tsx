import { MoreVertical, Plus, Trash2, Users } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import {
  useDeleteSpace,
  useGetSpacesQuery,
} from "@/controllers/API/queries/spaces";
import { CreateSpaceDialog } from "@/pages/SpacesPage/components/CreateSpaceDialog";
import type { SpaceWithStats } from "@/types/api";
import { cn } from "@/utils/utils";

export function SpacesSidebarSection() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { spaceId } = useParams<{ spaceId: string }>();
  const [showAllSpaces, setShowAllSpaces] = useState(false);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);

  const { data: spaces = [], isLoading } = useGetSpacesQuery();
  const { mutateAsync: deleteSpace } = useDeleteSpace();

  // Get spaces to display (max 5 or all)
  const getDisplayedSpaces = (): SpaceWithStats[] => {
    if (showAllSpaces || spaces.length <= 5) {
      return spaces;
    }
    // Show first 5 spaces (no recent tracking for now)
    return spaces.slice(0, 5);
  };

  const handleSpaceClick = (id: number) => {
    navigate(`/spaces/${id}/chats`);
  };

  const handleDeleteSpace = async (id: number) => {
    try {
      await deleteSpace({ id });
      toast.success(t("spaces.deleteSuccess"));
    } catch (error) {
      toast.error(t("spaces.deleteError"));
    }
  };

  const displayedSpaces = getDisplayedSpaces();

  return (
    <>
      <SidebarGroup>
        <SidebarMenu>
          <Collapsible defaultOpen className="group/collapsible">
            <SidebarMenuItem>
              {/* 展开状态：显示可折叠触发器 */}
              <CollapsibleTrigger
                asChild
                className="group-data-[collapsible=icon]:hidden"
              >
                <SidebarMenuButton tooltip={t("navigation.spaces")}>
                  <Users className="h-4 w-4" />
                  <span className="flex-1">{t("navigation.spaces")}</span>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="ml-auto h-5 w-5 group-data-[state=closed]/collapsible:hidden"
                    onClick={(e) => {
                      e.stopPropagation();
                      setIsCreateDialogOpen(true);
                    }}
                  >
                    <Plus className="h-4 w-4" />
                  </Button>
                </SidebarMenuButton>
              </CollapsibleTrigger>

              {/* 收缩状态：显示带 HoverCard 的图标 */}
              <div className="hidden group-data-[collapsible=icon]:flex flex-1 justify-center">
                <HoverCard openDelay={200} closeDelay={100}>
                  <HoverCardTrigger asChild>
                    <SidebarMenuButton
                      tooltip={t("navigation.spaces")}
                      className="w-auto"
                    >
                      <Users className="h-4 w-4" />
                    </SidebarMenuButton>
                  </HoverCardTrigger>
                  <HoverCardContent
                    side="right"
                    align="start"
                    className="w-64 p-2"
                  >
                    <div className="font-semibold mb-2 px-2">
                      {t("navigation.spaces")}
                    </div>
                    <div className="space-y-1">
                      {isLoading ? (
                        <div className="px-2 py-1.5 text-sm text-muted-foreground">
                          {t("common.loading")}
                        </div>
                      ) : displayedSpaces.length === 0 ? (
                        <div className="px-2 py-1.5 text-sm text-muted-foreground">
                          {t("spaces.noSpacesYet")}
                        </div>
                      ) : (
                        <>
                          {displayedSpaces.map((spaceWithStats) => {
                            const space = spaceWithStats.space;
                            const isActive = String(space.id) === spaceId;

                            return (
                              <button
                                key={space.id}
                                onClick={() => handleSpaceClick(space.id)}
                                className={cn(
                                  "w-full text-left px-2 py-1.5 rounded-md text-sm hover:bg-accent transition-colors",
                                  isActive && "bg-accent font-medium",
                                )}
                              >
                                {space.name}
                              </button>
                            );
                          })}
                          {spaces.length > 5 && (
                            <button
                              onClick={() => setShowAllSpaces(!showAllSpaces)}
                              className="w-full text-left px-2 py-1.5 rounded-md text-sm text-muted-foreground hover:bg-accent transition-colors"
                            >
                              {showAllSpaces
                                ? t("navigation.collapse")
                                : t("navigation.viewAll", {
                                    count: spaces.length,
                                  })}
                            </button>
                          )}
                        </>
                      )}
                    </div>
                  </HoverCardContent>
                </HoverCard>
              </div>

              <CollapsibleContent className="group-data-[collapsible=icon]:hidden">
                <SidebarMenu>
                  {isLoading ? (
                    <div className="px-3 py-2 text-sm text-muted-foreground">
                      {t("common.loading")}
                    </div>
                  ) : displayedSpaces.length === 0 ? (
                    <div className="px-3 py-2 text-sm text-muted-foreground">
                      {t("spaces.noSpacesYet")}
                    </div>
                  ) : (
                    <>
                      {displayedSpaces.map((spaceWithStats) => {
                        const space = spaceWithStats.space;
                        const isActive = String(space.id) === spaceId;

                        return (
                          <SidebarMenuItem key={space.id}>
                            <SidebarMenuButton
                              isActive={isActive}
                              onClick={() => handleSpaceClick(space.id)}
                              className="flex items-center justify-between"
                            >
                              <div className="flex items-center gap-2 overflow-hidden">
                                <span className="truncate group-data-[collapsible=icon]:hidden">
                                  {space.name}
                                </span>
                              </div>

                              <DropdownMenu>
                                <DropdownMenuTrigger
                                  asChild
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-5 w-5 shrink-0 group-data-[collapsible=icon]:hidden"
                                  >
                                    <MoreVertical className="h-3 w-3" />
                                  </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end">
                                  <DropdownMenuItem
                                    onClick={() => handleDeleteSpace(space.id)}
                                    className="text-destructive"
                                  >
                                    <Trash2 className="mr-2 h-4 w-4" />
                                    {t("navigation.deleteSpace")}
                                  </DropdownMenuItem>
                                </DropdownMenuContent>
                              </DropdownMenu>
                            </SidebarMenuButton>
                          </SidebarMenuItem>
                        );
                      })}

                      {/* View All button */}
                      {spaces.length > 5 && (
                        <SidebarMenuItem>
                          <SidebarMenuButton
                            onClick={() => setShowAllSpaces(!showAllSpaces)}
                            className="text-muted-foreground"
                          >
                            <span className="group-data-[collapsible=icon]:hidden">
                              {showAllSpaces
                                ? t("navigation.collapse")
                                : t("navigation.viewAll", {
                                    count: spaces.length,
                                  })}
                            </span>
                          </SidebarMenuButton>
                        </SidebarMenuItem>
                      )}
                    </>
                  )}
                </SidebarMenu>
              </CollapsibleContent>
            </SidebarMenuItem>
          </Collapsible>
        </SidebarMenu>
      </SidebarGroup>

      <CreateSpaceDialog
        open={isCreateDialogOpen}
        onOpenChange={setIsCreateDialogOpen}
      />
    </>
  );
}
