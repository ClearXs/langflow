import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import * as z from "zod";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { usePostCreateSpace } from "@/controllers/API/queries/spaces";

interface CreateSpaceDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CreateSpaceDialog({
  open,
  onOpenChange,
}: CreateSpaceDialogProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { mutateAsync: createSpace } = usePostCreateSpace();
  const [isCreating, setIsCreating] = useState(false);

  // Define schema with translated error messages
  const formSchema = z.object({
    name: z
      .string()
      .min(1, t("spaces.createDialog.nameRequired"))
      .max(100, t("spaces.createDialog.nameTooLong")),
    description: z
      .string()
      .max(500, t("spaces.createDialog.descriptionTooLong"))
      .optional(),
  });

  type FormValues = z.infer<typeof formSchema>;

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: "",
      description: "",
    },
  });

  const onSubmit = async (values: FormValues) => {
    try {
      setIsCreating(true);
      const newSpace = await createSpace({
        data: {
          name: values.name,
          description: values.description || null,
        },
      });

      toast.success(t("spaces.createDialog.successMessage"));
      form.reset();
      onOpenChange(false);

      // Navigate to the new space's chat page
      navigate(`/spaces/${newSpace.id}/chats`);
    } catch (error) {
      toast.error(t("spaces.createDialog.errorMessage"), {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>{t("spaces.createDialog.title")}</DialogTitle>
          <DialogDescription>
            {t("spaces.createDialog.description")}
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("spaces.createDialog.nameLabel")}</FormLabel>
                  <FormControl>
                    <Input
                      placeholder={t("spaces.createDialog.namePlaceholder")}
                      {...field}
                      disabled={isCreating}
                    />
                  </FormControl>
                  <FormDescription>
                    {t("spaces.createDialog.nameDescription")}
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    {t("spaces.createDialog.descriptionLabel")}
                  </FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder={t(
                        "spaces.createDialog.descriptionPlaceholder",
                      )}
                      {...field}
                      disabled={isCreating}
                      rows={3}
                    />
                  </FormControl>
                  <FormDescription>
                    {t("spaces.createDialog.descriptionDescription")}
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isCreating}
              >
                {t("spaces.createDialog.cancel")}
              </Button>
              <Button type="submit" disabled={isCreating}>
                {isCreating && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                {isCreating
                  ? t("spaces.createDialog.creating")
                  : t("spaces.createDialog.create")}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
