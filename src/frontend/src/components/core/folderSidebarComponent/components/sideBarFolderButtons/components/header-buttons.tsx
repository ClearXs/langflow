/*
 * @Author: dengchao dengchao
 * @Date: 2025-09-23 10:55:28
 * @LastEditors: dengchao dengchao
 * @LastEditTime: 2025-09-24 09:50:38
 * @FilePath: \frontend\src\components\core\folderSidebarComponent\components\sideBarFolderButtons\components\header-buttons.tsx
 * @Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
 */
import { useEffect, useState } from "react";
import IconComponent from "@/components/common/genericIconComponent";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { useUpdateUser } from "@/controllers/API/queries/auth";
import CustomGetStartedProgress from "@/customization/components/custom-get-started-progress";
import useAuthStore from "@/stores/authStore";
import { useUtilityStore } from "@/stores/utilityStore";
import { AddFolderButton } from "./add-folder-button";
import { UploadFolderButton } from "./upload-folder-button";
import { useTranslation } from "react-i18next";

export const HeaderButtons = ({
  handleUploadFlowsToFolder,
  isUpdatingFolder,
  isPending,
  addNewFolder,
}: {
  handleUploadFlowsToFolder: () => void;
  isUpdatingFolder: boolean;
  isPending: boolean;
  addNewFolder: () => void;
}) => {
  const { t } = useTranslation();
  const userData = useAuthStore((state) => state.userData);
  const hideGettingStartedProgress = useUtilityStore(
    (state) => state.hideGettingStartedProgress,
  );

  const [isDismissedDialog, setIsDismissedDialog] = useState(
    userData?.optins?.dialog_dismissed,
  );
  const [isGithubStarred, setIsGithubStarred] = useState(
    userData?.optins?.github_starred,
  );
  const [isDiscordJoined, setIsDiscordJoined] = useState(
    userData?.optins?.discord_clicked,
  );

  const { mutate: updateUser } = useUpdateUser();

  useEffect(() => {
    if (userData) {
      setIsDismissedDialog(userData.optins?.dialog_dismissed);
      setIsGithubStarred(userData.optins?.github_starred);
      setIsDiscordJoined(userData.optins?.discord_clicked);
    }
  }, [userData]);

  const handleDismissDialog = () => {
    setIsDismissedDialog(true);
    updateUser({
      user_id: userData?.id!,
      user: {
        optins: {
          ...userData?.optins,
          dialog_dismissed: true,
        },
      },
    });
  };

  return (
    <>
      {!hideGettingStartedProgress && !isDismissedDialog && userData && (
        <>
          <CustomGetStartedProgress
            userData={userData!}
            isGithubStarred={isGithubStarred ?? false}
            isDiscordJoined={isDiscordJoined ?? false}
            handleDismissDialog={handleDismissDialog}
          />

          <div className="-mx-4 mt-1 w-[280px]">
            <hr className="border-t-1 w-full" />
          </div>
        </>
      )}

      <div className="flex shrink-0 items-center justify-between gap-2 pt-2">
        <SidebarTrigger className="lg:hidden">
          <IconComponent name="PanelLeftClose" className="h-4 w-4" />
        </SidebarTrigger>

        <div className="flex-1 text-sm font-medium">{t("common.projects")}</div>
        <div className="flex items-center gap-1">
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
    </>
  );
};
