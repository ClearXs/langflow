import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { useGetDefaultSystemInstructionsQuery } from "@/controllers/API/queries/llm-configs";

interface SystemInstructionsEditorProps {
  spaceId: number;
}

export default function SystemInstructionsEditor({
  spaceId,
}: SystemInstructionsEditorProps) {
  const { t } = useTranslation();

  const [useDefault, setUseDefault] = useState(true);
  const [customInstructions, setCustomInstructions] = useState("");
  const [hasChanges, setHasChanges] = useState(false);

  const { data: defaultInstructionsResponse } =
    useGetDefaultSystemInstructionsQuery();

  // Update textarea when default toggle changes
  useEffect(() => {
    if (useDefault && defaultInstructionsResponse) {
      setCustomInstructions(defaultInstructionsResponse.instructions);
    }
  }, [useDefault, defaultInstructionsResponse]);

  const handleSave = async () => {
    try {
      // TODO: Implement save logic when backend API is available
      toast.success(t("spaces.settings.systemInstructionsEditor.saveSuccess"));
      setHasChanges(false);
    } catch (error: any) {
      toast.error(t("spaces.settings.systemInstructionsEditor.saveError"));
    }
  };

  const handleReset = () => {
    if (defaultInstructionsResponse) {
      setUseDefault(true);
      setCustomInstructions(defaultInstructionsResponse.instructions);
      setHasChanges(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h3 className="text-lg font-semibold">
          {t("spaces.settings.systemInstructionsEditor.title")}
        </h3>
        <p className="text-sm text-muted-foreground">
          {t("spaces.settings.systemInstructionsEditor.description")}
        </p>
      </div>

      {/* Editor Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base">
                {t("spaces.settings.systemInstructionsEditor.editorTitle")}
              </CardTitle>
              <CardDescription>
                {t(
                  "spaces.settings.systemInstructionsEditor.editorDescription",
                )}
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Switch
                id="use_default"
                checked={useDefault}
                onCheckedChange={(checked) => {
                  setUseDefault(checked);
                  setHasChanges(true);
                }}
              />
              <Label htmlFor="use_default" className="text-sm font-normal">
                {t("spaces.settings.useDefault")}
              </Label>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <Label htmlFor="system_instructions">
              {t("spaces.settings.systemInstructionsEditor.instructionsLabel")}
            </Label>
            <Textarea
              id="system_instructions"
              value={customInstructions}
              onChange={(e) => {
                setCustomInstructions(e.target.value);
                setHasChanges(true);
              }}
              disabled={useDefault}
              rows={12}
              className="font-mono text-sm"
              placeholder={t(
                "spaces.settings.systemInstructionsEditor.placeholder",
              )}
            />
            <p className="text-xs text-muted-foreground">
              {t("spaces.settings.systemInstructionsEditor.hint")}
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Action Buttons */}
      {hasChanges && (
        <div className="flex items-center gap-3 pt-4 border-t">
          <Button onClick={handleSave}>
            {t("spaces.settings.systemInstructionsEditor.saveChanges")}
          </Button>
          <Button variant="outline" onClick={handleReset}>
            {t("common.cancel")}
          </Button>
        </div>
      )}

      {/* Info Box */}
      <div className="rounded-lg bg-muted p-4">
        <h4 className="text-sm font-medium mb-2">
          {t(
            "spaces.settings.systemInstructionsEditor.whatAreSystemInstructions",
          )}
        </h4>
        <p className="text-sm text-muted-foreground">
          {t("spaces.settings.systemInstructionsEditor.explanation")}
        </p>
      </div>
    </div>
  );
}
