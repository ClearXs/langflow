import { useIsFetching, useIsMutating } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useParams } from "react-router-dom";
import ForwardedIconComponent from "@/components/common/genericIconComponent";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
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
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarSeparator,
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar";
import { useUpdateUser } from "@/controllers/API/queries/auth";
import {
  usePatchFolders,
  usePostFolders,
  usePostUploadFolders,
} from "@/controllers/API/queries/folders";
import { useGetDownloadFolders } from "@/controllers/API/queries/folders/use-get-download-folders";
import { CustomStoreButton } from "@/customization/components/custom-store-button";
import {
  ENABLE_CUSTOM_PARAM,
  ENABLE_DATASTAX_LANGFLOW,
  ENABLE_FILE_MANAGEMENT,
  ENABLE_KNOWLEDGE_BASES,
  ENABLE_MCP_NOTICE,
} from "@/customization/feature-flags";
import { useCustomNavigate } from "@/customization/hooks/use-custom-navigate";
import { track } from "@/customization/utils/analytics";
import { customGetDownloadFolderBlob } from "@/customization/utils/custom-get-download-folders";
import { createFileUpload } from "@/helpers/create-file-upload";
import { getObjectsFromFilelist } from "@/helpers/get-objects-from-filelist";
import useUploadFlow from "@/hooks/flows/use-upload-flow";
import { useIsMobile } from "@/hooks/use-mobile";
import useAuthStore from "@/stores/authStore";
import { getRecentFolders, trackFolderVisit } from "@/utils/recentFolders";
import type { FolderType } from "../../../../../pages/MainPage/entities";
import useAlertStore from "../../../../../stores/alertStore";
import useFlowsManagerStore from "../../../../../stores/flowsManagerStore";
import { useFolderStore } from "../../../../../stores/foldersStore";
import { useUtilityStore } from "../../../../../stores/utilityStore";
import { handleKeyDown } from "../../../../../utils/reactflowUtils";
import { cn } from "../../../../../utils/utils";
import useFileDrop from "../../hooks/use-on-file-drop";
import { SpacesSidebarSection } from "../SpacesSidebarSection";
import { SidebarFolderSkeleton } from "../sidebarFolderSkeleton";
import { AddFolderButton } from "./components/add-folder-button";
import { HeaderButtons } from "./components/header-buttons";
import { InputEditFolderName } from "./components/input-edit-folder-name";
import { MCPServerNotice } from "./components/mcp-server-notice";
import { SelectOptions } from "./components/select-options";
import { UploadFolderButton } from "./components/upload-folder-button";

type SideBarFoldersButtonsComponentProps = {
  handleChangeFolder?: (id: string) => void;
  handleDeleteFolder?: (item: FolderType) => void;
  handleFilesClick?: () => void;
};
const SideBarFoldersButtonsComponent = ({
  handleChangeFolder,
  handleDeleteFolder,
  handleFilesClick,
}: SideBarFoldersButtonsComponentProps) => {
  const { t } = useTranslation();
  const location = useLocation();
  const pathname = location.pathname;
  const folders = useFolderStore((state) => state.folders);
  const loading = !folders;
  const refInput = useRef<HTMLInputElement>(null);
  const hasAutoCollapsed = useRef<Set<string>>(new Set()); // Track which space IDs have been auto-collapsed
  const { setOpen } = useSidebar();

  const _navigate = useCustomNavigate();

  const currentFolder = pathname.split("/");
  const urlWithoutPath =
    pathname.split("/").length < (ENABLE_CUSTOM_PARAM ? 5 : 4);
  const checkPathFiles = pathname.includes("assets");

  const checkPathName = (itemId: string) => {
    if (urlWithoutPath && itemId === myCollectionId && !checkPathFiles) {
      return true;
    }
    return currentFolder.includes(itemId);
  };

  const setErrorData = useAlertStore((state) => state.setErrorData);
  const setSuccessData = useAlertStore((state) => state.setSuccessData);
  const isMobile = useIsMobile({ maxWidth: 1024 });
  const folderIdDragging = useFolderStore((state) => state.folderIdDragging);
  const myCollectionId = useFolderStore((state) => state.myCollectionId);
  const takeSnapshot = useFlowsManagerStore((state) => state.takeSnapshot);
  const defaultFolderName = useUtilityStore((state) => state.defaultFolderName);

  const folderId = useParams().folderId ?? myCollectionId ?? "";

  const { dragOver, dragEnter, dragLeave, onDrop } = useFileDrop(folderId);
  const uploadFlow = useUploadFlow();
  const [foldersNames, setFoldersNames] = useState({});
  const [editFolders, setEditFolderName] = useState(
    folders.map((obj) => ({ name: obj.name, edit: false })) ?? [],
  );

  const isFetchingFolders = !!useIsFetching({
    queryKey: ["useGetFolders"],
    exact: false,
  });

  const { mutate: mutateDownloadFolder } = useGetDownloadFolders({});
  const { mutate: mutateAddFolder, isPending } = usePostFolders();
  const { mutate: mutateUpdateFolder } = usePatchFolders();
  const { mutate } = usePostUploadFolders();

  const checkHoveringFolder = (folderId: string) => {
    if (folderId === folderIdDragging) {
      return "bg-accent text-accent-foreground";
    }
  };

  const isFetchingFolder = !!useIsFetching({
    queryKey: ["useGetFolder"],
    exact: false,
  });

  const isDeletingFolder = !!useIsMutating({
    mutationKey: ["useDeleteFolders"],
  });

  const isUpdatingFolder =
    isFetchingFolders ||
    isFetchingFolder ||
    isPending ||
    loading ||
    isDeletingFolder;

  const handleUploadFlowsToFolder = () => {
    createFileUpload().then((files: File[]) => {
      if (files?.length === 0) {
        return;
      }

      getObjectsFromFilelist<any>(files).then((objects) => {
        if (objects.every((flow) => flow.data?.nodes)) {
          uploadFlow({ files }).then(() => {
            setSuccessData({
              title: t("common.uploadedSuccessfully"),
            });
          });
        } else {
          files.forEach((folder) => {
            const formData = new FormData();
            formData.append("file", folder);
            mutate(
              { formData },
              {
                onSuccess: () => {
                  setSuccessData({
                    title: t("common.projectUploadedSuccessfully"),
                  });
                },
                onError: (err) => {
                  console.error(err);
                  setErrorData({
                    title: t("common.errorOnUploadingYourProject"),
                    list: [err["response"]["data"]["message"]],
                  });
                },
              },
            );
          });
        }
      });
    });
  };

  const handleDownloadFolder = (id: string, folderName: string) => {
    mutateDownloadFolder(
      {
        folderId: id,
      },
      {
        onSuccess: (response) => {
          customGetDownloadFolderBlob(response, id, folderName, setSuccessData);
        },
        onError: (e) => {
          setErrorData({
            title: t("common.errorOnDownloadingYourProject"),
          });
        },
      },
    );
  };

  function addNewFolder() {
    mutateAddFolder(
      {
        data: {
          name: t("common.newProject"),
          parent_id: null,
          description: "",
        },
      },
      {
        onSuccess: (folder) => {
          track(t("common.createNewProject"));
          handleChangeFolder!(folder.id);
        },
      },
    );
  }

  function handleEditFolderName(e, name): void {
    const {
      target: { value },
    } = e;
    setFoldersNames((old) => ({
      ...old,
      [name]: value,
    }));
  }

  useEffect(() => {
    if (folders && folders.length > 0) {
      setEditFolderName(
        folders.map((obj) => ({ name: obj.name, edit: false })),
      );
    }
  }, [folders]);

  // Auto-collapse sidebar when entering space details (only once per space)
  useEffect(() => {
    const spaceMatch = pathname.match(/^\/spaces\/(\d+)\//);
    if (spaceMatch) {
      const spaceId = spaceMatch[1];
      // Only auto-collapse if this space hasn't been auto-collapsed before
      if (!hasAutoCollapsed.current.has(spaceId)) {
        setOpen(false);
        hasAutoCollapsed.current.add(spaceId);
      }
    }
  }, [pathname, setOpen]);

  const handleEditNameFolder = async (item) => {
    const newEditFolders = editFolders.map((obj) => {
      if (obj.name === item.name) {
        return { name: item.name, edit: false };
      }
      return { name: obj.name, edit: false };
    });
    setEditFolderName(newEditFolders);
    if (foldersNames[item.name].trim() !== "") {
      setFoldersNames((old) => ({
        ...old,
        [item.name]: foldersNames[item.name],
      }));
      const body = {
        ...item,
        name: foldersNames[item.name],
        flows: item.flows?.length > 0 ? item.flows : [],
        components: item.components?.length > 0 ? item.components : [],
      };

      mutateUpdateFolder(
        {
          data: body,
          folderId: item.id!,
        },
        {
          onSuccess: (updatedFolder) => {
            const updatedFolderIndex = folders.findIndex(
              (f) => f.id === updatedFolder.id,
            );

            const updateFolders = [...folders];
            updateFolders[updatedFolderIndex] = updatedFolder;

            setFoldersNames({});
            setEditFolderName(
              folders.map((obj) => ({
                name: obj.name,
                edit: false,
              })),
            );
          },
        },
      );
    } else {
      setFoldersNames((old) => ({
        ...old,
        [item.name]: item.name,
      }));
    }
  };

  const handleDoubleClick = (event, item) => {
    if (item.name === defaultFolderName) {
      return;
    }

    event.stopPropagation();
    event.preventDefault();

    handleSelectFolderToRename(item);
  };

  const handleSelectFolderToRename = (item) => {
    if (!foldersNames[item.name]) {
      setFoldersNames({ [item.name]: item.name });
    }

    if (editFolders.find((obj) => obj.name === item.name)?.name) {
      const newEditFolders = editFolders.map((obj) => {
        if (obj.name === item.name) {
          return { name: item.name, edit: true };
        }
        return { name: obj.name, edit: false };
      });
      setEditFolderName(newEditFolders);
      takeSnapshot();
      return;
    }

    setEditFolderName((old) => [...old, { name: item.name, edit: true }]);
    setFoldersNames((oldFolder) => ({
      ...oldFolder,
      [item.name]: item.name,
    }));
    takeSnapshot();
  };

  const handleKeyDownFn = (e, item) => {
    if (e.key === "Escape") {
      const newEditFolders = editFolders.map((obj) => {
        if (obj.name === item.name) {
          return { name: item.name, edit: false };
        }
        return { name: obj.name, edit: false };
      });
      setEditFolderName(newEditFolders);
      setFoldersNames({});
      setEditFolderName(
        folders.map((obj) => ({
          name: obj.name,
          edit: false,
        })),
      );
    }
    if (e.key === "Enter") {
      refInput.current?.blur();
    }
  };

  const [hoveredFolderId, setHoveredFolderId] = useState<string | null>(null);
  const [showAllProjects, setShowAllProjects] = useState(false);

  // 获取要显示的项目列表 (Get list of projects to display)
  const displayedFolders = useMemo(() => {
    if (!folders || folders.length === 0) return [];

    // 如果显示全部或项目数 <= 5，返回所有项目
    // If showing all or total projects <= 5, return all projects
    if (showAllProjects || folders.length <= 5) {
      return folders;
    }

    // 获取最近访问的项目 ID
    // Get recently visited project IDs
    const recentIds = getRecentFolders(5);

    // 确保当前激活的项目在列表中
    // Ensure currently active project is in the list
    const activeFolderId = folderId;
    if (activeFolderId && !recentIds.includes(activeFolderId)) {
      recentIds.push(activeFolderId);
    }

    // 根据最近访问的 ID 过滤项目，保持顺序
    // Filter projects based on recent IDs, maintaining order
    const displayedFolders = recentIds
      .map((id) => folders.find((folder) => folder.id === id))
      .filter(Boolean)
      .slice(0, 5);

    return displayedFolders;
  }, [folders, showAllProjects, folderId]);

  const userData = useAuthStore((state) => state.userData);
  const { mutate: updateUser } = useUpdateUser();
  const userDismissedMcpDialog = userData?.optins?.mcp_dialog_dismissed;

  const [isDismissedMcpDialog, setIsDismissedMcpDialog] = useState(
    userDismissedMcpDialog,
  );

  const handleDismissMcpDialog = () => {
    setIsDismissedMcpDialog(true);
    updateUser({
      user_id: userData?.id!,
      user: {
        optins: {
          ...userData?.optins,
          mcp_dialog_dismissed: true,
        },
      },
    });
  };

  // 包装 handleChangeFolder 以追踪访问
  // Wrap handleChangeFolder to track visits
  const handleChangeFolderWithTracking = (id: string) => {
    trackFolderVisit(id);
    handleChangeFolder!(id);
  };

  return (
    <Sidebar collapsible="icon" data-testid="project-sidebar">
      <SidebarHeader className="px-4 py-1">
        <HeaderButtons
          handleUploadFlowsToFolder={handleUploadFlowsToFolder}
          isUpdatingFolder={isUpdatingFolder}
          isPending={isPending}
          addNewFolder={addNewFolder}
        />
      </SidebarHeader>
      <SidebarContent>
        {/* 分组1: 我的项目 / Group 1: My Projects */}
        <SidebarGroup className="p-4 py-2">
          <SidebarMenu>
            <Collapsible defaultOpen className="group/collapsible">
              <SidebarMenuItem>
                <div className="flex items-center justify-between w-full">
                  {/* 展开状态：显示可折叠触发器 */}
                  <CollapsibleTrigger
                    asChild
                    className="group-data-[collapsible=icon]:hidden"
                  >
                    <SidebarMenuButton
                      tooltip={t("navigation.myProjects")}
                      className="flex-1"
                    >
                      <ForwardedIconComponent
                        name="Folder"
                        className="h-4 w-4"
                      />
                      <span>{t("navigation.myProjects")}</span>
                    </SidebarMenuButton>
                  </CollapsibleTrigger>

                  {/* 收缩状态：显示带 HoverCard 的图标 */}
                  <div className="hidden group-data-[collapsible=icon]:flex flex-1 justify-center">
                    <HoverCard openDelay={200} closeDelay={100}>
                      <HoverCardTrigger asChild>
                        <SidebarMenuButton
                          tooltip={t("navigation.myProjects")}
                          className="w-auto"
                        >
                          <ForwardedIconComponent
                            name="Folder"
                            className="h-4 w-4"
                          />
                        </SidebarMenuButton>
                      </HoverCardTrigger>
                      <HoverCardContent
                        side="right"
                        align="start"
                        className="w-64 p-2"
                      >
                        <div className="font-semibold mb-2 px-2">
                          {t("navigation.myProjects")}
                        </div>
                        <div className="space-y-1">
                          {displayedFolders.map((item) => (
                            <button
                              key={item.id}
                              onClick={() => {
                                handleChangeFolderWithTracking(item.id!);
                              }}
                              className={cn(
                                "w-full text-left px-2 py-1.5 rounded-md text-sm hover:bg-accent transition-colors",
                                checkPathName(item.id!) &&
                                  "bg-accent font-medium",
                              )}
                            >
                              {item.name}
                            </button>
                          ))}
                          {folders.length > 5 && (
                            <button
                              onClick={() =>
                                setShowAllProjects(!showAllProjects)
                              }
                              className="w-full text-left px-2 py-1.5 rounded-md text-sm text-muted-foreground hover:bg-accent transition-colors"
                            >
                              {showAllProjects
                                ? t("navigation.collapse")
                                : t("navigation.viewAll", {
                                    count: folders.length,
                                  })}
                            </button>
                          )}
                        </div>
                      </HoverCardContent>
                    </HoverCard>
                  </div>

                  <div className="flex items-center gap-1 group-data-[collapsible=icon]:hidden">
                    <UploadFolderButton
                      onClick={handleUploadFlowsToFolder}
                      disabled={isUpdatingFolder}
                    />
                    <AddFolderButton
                      onClick={addNewFolder}
                      disabled={isUpdatingFolder}
                      loading={isPending}
                    />
                  </div>
                </div>
                <CollapsibleContent className="group-data-[collapsible=icon]:hidden">
                  <SidebarMenu>
                    {!loading ? (
                      <>
                        {displayedFolders.map((item, index) => {
                          const editFolderName = editFolders?.filter(
                            (folder) => folder.name === item.name,
                          )[0];
                          return (
                            <SidebarMenuItem
                              key={index}
                              className="group/menu-button"
                              onMouseEnter={() => setHoveredFolderId(item.id!)}
                              onMouseLeave={() => setHoveredFolderId(null)}
                            >
                              <div className="relative flex w-full">
                                <SidebarMenuButton
                                  size="md"
                                  onDragOver={(e) => dragOver(e, item.id!)}
                                  onDragEnter={(e) => dragEnter(e, item.id!)}
                                  onDragLeave={dragLeave}
                                  onDrop={(e) => onDrop(e, item.id!)}
                                  key={item.id}
                                  data-testid={`sidebar-nav-${item.name}`}
                                  id={`sidebar-nav-${item.name}`}
                                  isActive={checkPathName(item.id!)}
                                  onClick={() =>
                                    handleChangeFolderWithTracking(item.id!)
                                  }
                                  className={cn(
                                    "flex-grow pr-8",
                                    hoveredFolderId === item.id && "bg-accent",
                                    checkHoveringFolder(item.id!),
                                  )}
                                >
                                  <div
                                    onDoubleClick={(event) => {
                                      handleDoubleClick(event, item);
                                    }}
                                    className="flex w-full items-center justify-between gap-2"
                                  >
                                    <div className="flex flex-1 items-center gap-2">
                                      {editFolderName?.edit &&
                                      !isUpdatingFolder ? (
                                        <InputEditFolderName
                                          handleEditFolderName={
                                            handleEditFolderName
                                          }
                                          item={item}
                                          refInput={refInput}
                                          handleKeyDownFn={handleKeyDownFn}
                                          handleEditNameFolder={
                                            handleEditNameFolder
                                          }
                                          editFolderName={editFolderName}
                                          foldersNames={foldersNames}
                                          handleKeyDown={handleKeyDown}
                                        />
                                      ) : (
                                        <span className="block w-0 grow truncate text-sm group-data-[collapsible=icon]:hidden">
                                          {item.name}
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                </SidebarMenuButton>
                                <div
                                  className="absolute right-2 top-[0.45rem] flex items-center hover:text-foreground"
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  <SelectOptions
                                    item={item}
                                    index={index}
                                    handleDeleteFolder={handleDeleteFolder}
                                    handleDownloadFolder={() =>
                                      handleDownloadFolder(item.id!, item.name)
                                    }
                                    handleSelectFolderToRename={
                                      handleSelectFolderToRename
                                    }
                                    checkPathName={checkPathName}
                                  />
                                </div>
                              </div>
                            </SidebarMenuItem>
                          );
                        })}

                        {/* 如果超过5个项目，显示"查看全部"按钮 / Show "View All" if more than 5 projects */}
                        {folders.length > 5 && (
                          <SidebarMenuItem>
                            <SidebarMenuButton
                              size="md"
                              onClick={() =>
                                setShowAllProjects(!showAllProjects)
                              }
                              className="text-muted-foreground hover:text-foreground"
                            >
                              <ForwardedIconComponent
                                name={showAllProjects ? "ChevronUp" : "List"}
                                className="h-4 w-4"
                              />
                              <span className="group-data-[collapsible=icon]:hidden">
                                {showAllProjects
                                  ? t("navigation.collapse")
                                  : t("navigation.viewAll", {
                                      count: folders.length,
                                    })}
                              </span>
                            </SidebarMenuButton>
                          </SidebarMenuItem>
                        )}
                      </>
                    ) : (
                      <>
                        <SidebarFolderSkeleton />
                        <SidebarFolderSkeleton />
                      </>
                    )}
                  </SidebarMenu>
                </CollapsibleContent>
              </SidebarMenuItem>
            </Collapsible>
          </SidebarMenu>
        </SidebarGroup>

        <SidebarSeparator className="group-data-[collapsible=icon]:hidden" />

        {/* 分组2: 空间 / Group 2: Spaces */}
        <SpacesSidebarSection />

        <div className="flex-1" />

        {ENABLE_MCP_NOTICE && !isDismissedMcpDialog && (
          <div className="p-2">
            <MCPServerNotice handleDismissDialog={handleDismissMcpDialog} />
          </div>
        )}
      </SidebarContent>

      <SidebarFooter className="border-t p-2">
        {ENABLE_FILE_MANAGEMENT && ENABLE_DATASTAX_LANGFLOW && (
          <div className="mb-2">
            <CustomStoreButton />
          </div>
        )}
        <SidebarTrigger className="w-full">
          <ForwardedIconComponent name="PanelLeftClose" className="h-4 w-4" />
        </SidebarTrigger>
      </SidebarFooter>
    </Sidebar>
  );
};
export default SideBarFoldersButtonsComponent;
