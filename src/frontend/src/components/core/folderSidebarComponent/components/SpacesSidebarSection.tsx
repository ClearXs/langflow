import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { Users, LayoutGrid, Plus, MoreVertical, Trash2 } from "lucide-react";
import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
} from "@/components/ui/sidebar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { useGetSpacesQuery } from "@/controllers/API/queries/spaces";
import { useDeleteSpace } from "@/controllers/API/queries/spaces";
import { CreateSpaceDialog } from "@/pages/SpacesPage/components/CreateSpaceDialog";
import { getRecentSpaces, trackSpaceVisit } from "@/utils/recentSpaces";
import { toast } from "sonner";
import type { SpaceWithStats } from "@/types/api";

export function SpacesSidebarSection() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { spaceId } = useParams<{ spaceId: string }>();
  const [showAllSpaces, setShowAllSpaces] = useState(false);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);

  const { data: spaces = [], isLoading } = useGetSpacesQuery();
  const { mutateAsync: deleteSpace } = useDeleteSpace();

  // Get spaces to display (max 5 recent + current active)
  const getDisplayedSpaces = (): SpaceWithStats[] => {
    if (showAllSpaces || spaces.length <= 5) {
      return spaces;
    }

    const recentSpaceIds = getRecentSpaces(5);
    const activeSpaceId = spaceId;

    // Map IDs to full SpaceWithStats objects
    const recentSpaces = recentSpaceIds
      .map((id) => spaces.find((s) => String(s.space.id) === id))
      .filter((s): s is SpaceWithStats => s !== undefined);

    // If current active space not in recent list, add it
    if (
      activeSpaceId &&
      !recentSpaces.find((s) => String(s.space.id) === activeSpaceId)
    ) {
      const activeSpace = spaces.find(
        (s) => String(s.space.id) === activeSpaceId,
      );
      if (activeSpace && recentSpaces.length < 5) {
        recentSpaces.push(activeSpace);
      }
    }

    return recentSpaces.slice(0, 5);
  };

  const handleSpaceClick = (id: number) => {
    trackSpaceVisit(String(id));
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
        <SidebarGroupLabel>
          <Users className="mr-2 h-4 w-4" />
          {t("sidebar.navigation.spaces")}
          <Button
            variant="ghost"
            size="icon"
            className="ml-auto h-5 w-5"
            onClick={() => setIsCreateDialogOpen(true)}
          >
            <Plus className="h-4 w-4" />
          </Button>
        </SidebarGroupLabel>

        <SidebarGroupContent>
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
                          <LayoutGrid className="h-4 w-4 shrink-0" />
                          <span className="truncate">{space.name}</span>
                        </div>

                        <DropdownMenu>
                          <DropdownMenuTrigger
                            asChild
                            onClick={(e) => e.stopPropagation()}
                          >
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-5 w-5 shrink-0"
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
                              {t("sidebar.navigation.deleteSpace")}
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
                      <LayoutGrid className="mr-2 h-4 w-4" />
                      {showAllSpaces
                        ? t("sidebar.navigation.collapse")
                        : t("sidebar.navigation.viewAll", {
                            count: spaces.length,
                          })}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                )}
              </>
            )}
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>

      <CreateSpaceDialog
        open={isCreateDialogOpen}
        onOpenChange={setIsCreateDialogOpen}
      />
    </>
  );
}
