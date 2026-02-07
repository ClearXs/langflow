import { Loader2 } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface ConnectorConfigDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  connectorId: string;
  connectorName: string;
  connectorIcon: React.ReactNode;
  spaceId: number;
  onSuccess?: () => void;
}

export function ConnectorConfigDialog({
  open,
  onOpenChange,
  connectorId,
  connectorName,
  connectorIcon,
  spaceId,
  onSuccess,
}: ConnectorConfigDialogProps) {
  const { t } = useTranslation();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [connectorName_input, setConnectorNameInput] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [syncInterval, setSyncInterval] = useState("60");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!connectorName_input.trim()) {
      toast.error(t("spaces.documents.connectors.config.errors.name_required"));
      return;
    }

    if (!apiKey.trim()) {
      toast.error(t("spaces.documents.connectors.config.errors.api_key_required"));
      return;
    }

    setIsSubmitting(true);

    try {
      // TODO: Implement API call to configure connector
      // const response = await api.post('/api/v1/connectors/configure', {
      //   connector_type: connectorId,
      //   connector_name: connectorName_input,
      //   api_key: apiKey,
      //   sync_interval_minutes: parseInt(syncInterval),
      //   space_id: spaceId,
      // });

      // Simulate API call for now
      await new Promise((resolve) => setTimeout(resolve, 2000));

      toast.success(
        t("spaces.documents.connectors.config.success", { name: connectorName }),
      );
      setConnectorNameInput("");
      setApiKey("");
      setSyncInterval("60");
      onOpenChange(false);
      onSuccess?.();
    } catch (error) {
      toast.error(
        t("spaces.documents.connectors.config.error", {
          error: error instanceof Error ? error.message : "Unknown error",
        }),
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <div className="flex items-center gap-3 mb-2">
            <div className="rounded-lg bg-muted p-2">{connectorIcon}</div>
            <div>
              <DialogTitle>
                {t("spaces.documents.connectors.config.title", { name: connectorName })}
              </DialogTitle>
              <DialogDescription>
                {t("spaces.documents.connectors.config.description", { name: connectorName })}
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Connector Name */}
          <div className="space-y-2">
            <Label htmlFor="connector-name">
              {t("spaces.documents.connectors.config.fields.name")}
            </Label>
            <Input
              id="connector-name"
              placeholder={t("spaces.documents.connectors.config.fields.name_placeholder", { name: connectorName })}
              value={connectorName_input}
              onChange={(e) => setConnectorNameInput(e.target.value)}
              disabled={isSubmitting}
              required
            />
            <p className="text-xs text-muted-foreground">
              {t("spaces.documents.connectors.config.fields.name_hint")}
            </p>
          </div>

          {/* API Key */}
          <div className="space-y-2">
            <Label htmlFor="api-key">
              {t("spaces.documents.connectors.config.fields.api_key")}
            </Label>
            <Input
              id="api-key"
              type="password"
              placeholder="••••••••••••••••"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              disabled={isSubmitting}
              required
            />
            <p className="text-xs text-muted-foreground">
              {t("spaces.documents.connectors.config.fields.api_key_hint")}
            </p>
          </div>

          {/* Sync Interval */}
          <div className="space-y-2">
            <Label htmlFor="sync-interval">
              {t("spaces.documents.connectors.config.fields.sync_interval")}
            </Label>
            <Select
              value={syncInterval}
              onValueChange={setSyncInterval}
              disabled={isSubmitting}
            >
              <SelectTrigger id="sync-interval">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="15">
                  {t("spaces.documents.connectors.config.intervals.15min")}
                </SelectItem>
                <SelectItem value="30">
                  {t("spaces.documents.connectors.config.intervals.30min")}
                </SelectItem>
                <SelectItem value="60">
                  {t("spaces.documents.connectors.config.intervals.1hour")}
                </SelectItem>
                <SelectItem value="120">
                  {t("spaces.documents.connectors.config.intervals.2hours")}
                </SelectItem>
                <SelectItem value="360">
                  {t("spaces.documents.connectors.config.intervals.6hours")}
                </SelectItem>
                <SelectItem value="720">
                  {t("spaces.documents.connectors.config.intervals.12hours")}
                </SelectItem>
                <SelectItem value="1440">
                  {t("spaces.documents.connectors.config.intervals.24hours")}
                </SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              {t("spaces.documents.connectors.config.fields.sync_interval_hint")}
            </p>
          </div>

          {/* Info Box */}
          <div className="rounded-lg border bg-muted/30 p-3 space-y-2">
            <p className="text-sm font-medium">
              {t("spaces.documents.connectors.config.info.title")}
            </p>
            <ul className="text-xs text-muted-foreground space-y-1">
              <li>
                • {t("spaces.documents.connectors.config.info.auto_sync")}
              </li>
              <li>
                • {t("spaces.documents.connectors.config.info.incremental")}
              </li>
              <li>
                • {t("spaces.documents.connectors.config.info.security")}
              </li>
            </ul>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isSubmitting}
            >
              {t("common.cancel")}
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t("spaces.documents.connectors.config.configuring")}
                </>
              ) : (
                t("spaces.documents.connectors.config.configure")
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
