import { Plug, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export default function ConnectorsPage() {
  return (
    <div className="h-full flex items-center justify-center p-8">
      <Card className="max-w-md border-dashed">
        <CardContent className="flex flex-col items-center justify-center py-16">
          <div className="rounded-full bg-muted p-4 mb-4">
            <Plug className="h-8 w-8 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold mb-2">Connectors</h3>
          <p className="text-muted-foreground text-center max-w-sm mb-6">
            Connect external data sources to this space. Connectors
            functionality coming soon.
          </p>
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            Add Connector
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
