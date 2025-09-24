/*
 * @Author: dengchao dengchao
 * @Date: 2025-09-23 10:55:28
 * @LastEditors: dengchao dengchao
 * @LastEditTime: 2025-09-24 09:53:16
 * @FilePath: \frontend\src\components\core\folderSidebarComponent\components\sideBarFolderButtons\components\add-folder-button.tsx
 * @Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
 */
import IconComponent from "@/components/common/genericIconComponent";
import ShadTooltip from "@/components/common/shadTooltipComponent";
import { Button } from "@/components/ui/button";
import { useTranslation } from "react-i18next";

export const AddFolderButton = ({
  onClick,
  disabled,
  loading,
}: {
  onClick: () => void;
  disabled: boolean;
  loading: boolean;
}) => {
  const { t } = useTranslation();
  return (
  <ShadTooltip content={t("common.createNewProject")} styleClasses="z-50">
    <Button
      variant="ghost"
      size="icon"
      className="h-7 w-7 border-0 text-zinc-500 hover:bg-zinc-200 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-white"
      onClick={onClick}
      data-testid="add-project-button"
      disabled={disabled}
      loading={loading}
    >
      <IconComponent name="Plus" className="h-4 w-4" />
    </Button>
  </ShadTooltip>
  );
};
