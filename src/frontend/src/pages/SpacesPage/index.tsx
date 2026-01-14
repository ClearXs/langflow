import { formatDistanceToNow } from "date-fns";
import { FileText, Plus, Search, Users } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import SideBarFoldersButtonsComponent from "@/components/core/folderSidebarComponent/components/sideBarFolderButtons";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { SidebarProvider } from "@/components/ui/sidebar";
import { useGetSpacesQuery } from "@/controllers/API/queries/spaces";
import { useCustomNavigate } from "@/customization/hooks/use-custom-navigate";
import { CreateSpaceDialog } from "./components/CreateSpaceDialog";

export default function SpacesPage() {
  const { t } = useTranslation();
  const [searchQuery, setSearchQuery] = useState("");
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const navigate = useCustomNavigate();

  const { data: spaces = [], isLoading } = useGetSpacesQuery();

  const filteredSpaces = spaces.filter((spaceWithStats) =>
    spaceWithStats.space.name.toLowerCase().includes(searchQuery.toLowerCase()),
  );

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
      <main className="flex-1 overflow-auto">
        <div className="container mx-auto py-10 px-4">
          {/* Header */}
          <div className="flex flex-col gap-6 mb-8">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold tracking-tight">
                  {t("spaces.title")}
                </h1>
                <p className="text-muted-foreground mt-2">
                  {t("spaces.subtitle")}
                </p>
              </div>
              <Button onClick={() => setIsCreateDialogOpen(true)} size="lg">
                <Plus className="mr-2 h-4 w-4" />
                {t("spaces.createSpace")}
              </Button>
            </div>

            {/* Search */}
            <div className="relative max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder={t("spaces.searchPlaceholder")}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>

          {/* Loading State */}
          {isLoading && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[1, 2, 3].map((i) => (
                <Card key={i} className="animate-pulse">
                  <CardHeader>
                    <div className="h-6 bg-muted rounded w-3/4" />
                    <div className="h-4 bg-muted rounded w-full mt-2" />
                  </CardHeader>
                  <CardContent>
                    <div className="h-16 bg-muted rounded" />
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* Empty State */}
          {!isLoading && filteredSpaces.length === 0 && (
            <Card className="border-dashed">
              <CardContent className="flex flex-col items-center justify-center py-16">
                <div className="rounded-full bg-muted p-4 mb-4">
                  <Plus className="h-8 w-8 text-muted-foreground" />
                </div>
                <h3 className="text-lg font-semibold mb-2">
                  {searchQuery
                    ? t("spaces.noSpacesFound")
                    : t("spaces.noSpacesYet")}
                </h3>
                <p className="text-muted-foreground text-center max-w-sm mb-6">
                  {searchQuery
                    ? t("spaces.adjustSearchQuery")
                    : t("spaces.getStartedMessage")}
                </p>
                {!searchQuery && (
                  <Button onClick={() => setIsCreateDialogOpen(true)}>
                    <Plus className="mr-2 h-4 w-4" />
                    {t("spaces.createFirstSpace")}
                  </Button>
                )}
              </CardContent>
            </Card>
          )}

          {/* Spaces Grid */}
          {!isLoading && filteredSpaces.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredSpaces.map((spaceWithStats) => (
                <Link
                  key={spaceWithStats.space.id}
                  to={`/spaces/${spaceWithStats.space.id}/chats`}
                >
                  <Card className="h-full hover:shadow-lg transition-shadow cursor-pointer">
                    <CardHeader>
                      <CardTitle className="flex items-start justify-between">
                        <span className="line-clamp-1">
                          {spaceWithStats.space.name}
                        </span>
                        {spaceWithStats.space.is_shared && (
                          <span className="text-xs bg-primary/10 text-primary px-2 py-1 rounded-full">
                            {t("spaces.shared")}
                          </span>
                        )}
                      </CardTitle>
                      {spaceWithStats.space.description && (
                        <CardDescription className="line-clamp-2">
                          {spaceWithStats.space.description}
                        </CardDescription>
                      )}
                    </CardHeader>

                    <CardContent>
                      <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        <div className="flex items-center gap-1">
                          <Users className="h-4 w-4" />
                          <span>
                            {spaceWithStats.member_count} {t("spaces.members")}
                          </span>
                        </div>
                        <div className="flex items-center gap-1">
                          <FileText className="h-4 w-4" />
                          <span>
                            {spaceWithStats.document_count} {t("spaces.docs")}
                          </span>
                        </div>
                      </div>
                    </CardContent>

                    <CardFooter className="text-xs text-muted-foreground">
                      {t("spaces.updated")}{" "}
                      {formatDistanceToNow(
                        new Date(spaceWithStats.space.updated_at),
                        {
                          addSuffix: true,
                        },
                      )}
                    </CardFooter>
                  </Card>
                </Link>
              ))}
            </div>
          )}

          {/* Create Space Dialog */}
          <CreateSpaceDialog
            open={isCreateDialogOpen}
            onOpenChange={setIsCreateDialogOpen}
          />
        </div>
      </main>
    </SidebarProvider>
  );
}
