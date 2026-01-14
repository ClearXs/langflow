import { Settings as SettingsIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

export default function SettingsPage() {
  return (
    <div className="h-full flex items-center justify-center p-8">
      <Card className="max-w-md border-dashed">
        <CardContent className="flex flex-col items-center justify-center py-16">
          <div className="rounded-full bg-muted p-4 mb-4">
            <SettingsIcon className="h-8 w-8 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold mb-2">Space Settings</h3>
          <p className="text-muted-foreground text-center max-w-sm">
            Configure settings for this space. Settings functionality coming
            soon.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
