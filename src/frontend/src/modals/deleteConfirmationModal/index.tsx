/*
 * @Author: dengchao dengchao
 * @Date: 2025-09-23 10:55:29
 * @LastEditors: dengchao dengchao
 * @LastEditTime: 2025-09-24 14:25:00
 * @FilePath: \frontend\src\modals\deleteConfirmationModal\index.tsx
 * @Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
 */
import { DialogClose } from "@radix-ui/react-dialog";
import { Trash2 } from "lucide-react";
import { Button } from "../../components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "../../components/ui/dialog";
import { useTranslation } from "react-i18next";
export default function DeleteConfirmationModal({
  children,
  onConfirm,
  description,
  asChild,
  open,
  setOpen,
  note = "",
}: {
  children?: JSX.Element;
  onConfirm: (e: React.MouseEvent<HTMLButtonElement, MouseEvent>) => void;
  description?: string;
  asChild?: boolean;
  open?: boolean;
  setOpen?: (open: boolean) => void;
  note?: string;
}) {
  const { t } = useTranslation();
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild={!children ? true : asChild} tabIndex={-1}>
        {children ?? <></>}
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            <div className="flex items-center">
              <Trash2
                className="h-6 w-6 pr-1 text-foreground"
                strokeWidth={1.5}
              />
              <span className="pl-2">{t("common.delete")}</span>
            </div>
          </DialogTitle>
        </DialogHeader>
        <span className="pb-3 text-sm">
          {t("common.thisWillPermanentlyDeleteThe")} {description ?? "flow"}
          {note ? " " + note : ""}{t("common.dot")}<br />
          <br />
          {t("common.thisCantBeUndone")}
        </span>
        <DialogFooter>
          <DialogClose asChild>
            <Button
              onClick={(e) => e.stopPropagation()}
              className="mr-1"
              variant="outline"
              data-testid="btn_cancel_delete_confirmation_modal"
            >
              {t("common.cancel")}
            </Button>
          </DialogClose>
          <DialogClose asChild>
            <Button
              type="submit"
              variant="destructive"
              onClick={(e) => {
                onConfirm(e);
              }}
              data-testid="btn_delete_delete_confirmation_modal"
            >
              {t("common.delete")}
            </Button>
          </DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
