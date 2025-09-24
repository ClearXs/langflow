/*
 * @Author: dengchao dengchao
 * @Date: 2025-09-23 10:55:29
 * @LastEditors: dengchao dengchao
 * @LastEditTime: 2025-09-24 14:00:42
 * @FilePath: \frontend\src\pages\MainPage\components\modalsComponent\index.tsx
 * @Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
 */
// Modals.tsx
import TemplatesModal from "@/modals/templatesModal";
import DeleteConfirmationModal from "../../../../modals/deleteConfirmationModal";
import { useTranslation } from "react-i18next";

interface ModalsProps {
  openModal: boolean;
  setOpenModal: (value: boolean) => void;
  openDeleteFolderModal: boolean;
  setOpenDeleteFolderModal: (value: boolean) => void;
  handleDeleteFolder: () => void;
}

const ModalsComponent = ({
  openModal = false,
  setOpenModal = () => {},
  openDeleteFolderModal = false,
  setOpenDeleteFolderModal = () => {},
  handleDeleteFolder = () => {},
}: ModalsProps) => {
  const { t } = useTranslation();
  return (
  <>
    {openModal && <TemplatesModal open={openModal} setOpen={setOpenModal} />}
    {openDeleteFolderModal && (
      <DeleteConfirmationModal
        open={openDeleteFolderModal}
        setOpen={setOpenDeleteFolderModal}
        onConfirm={() => {
          handleDeleteFolder();
          setOpenDeleteFolderModal(false);
        }}
        description={t("common.folder")}
        note={t("common.andAllAssociatedFlowsAndComponents")}
      >
        <></>
      </DeleteConfirmationModal>
      )}
    </>
  );
};

export default ModalsComponent;
