import { MoreVertical, Plus, Trash2, Users } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
        <SidebarGroupLabel>
          <Users className="mr-2 h-4 w-4" />
          {t("navigation.spaces")}
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
                      {showAllSpaces
                        ? t("navigation.collapse")
                        : t("navigation.viewAll", {
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
