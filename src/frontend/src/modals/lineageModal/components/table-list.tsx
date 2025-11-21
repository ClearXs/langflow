import ForwardedIconComponent from "@/components/common/genericIconComponent";
import { Button } from "@/components/ui/button";
import type { LineageTable } from "../use-get-lineage";

interface TableListProps {
  tables: LineageTable[];
  onTableClick: (tableId: string) => void;
}

const TableList = ({ tables, onTableClick }: TableListProps) => {
  if (tables.length === 0) {
    return <div className="text-sm text-muted-foreground">No tables found</div>;
  }

  return (
    <div className="space-y-1">
      {tables.map((table) => (
        <Button
          key={table.id}
          variant="ghost"
          size="sm"
          className="w-full justify-start gap-2 text-left"
          onClick={() => onTableClick(table.table_name)}
        >
          <ForwardedIconComponent
            name="Database"
            className="h-4 w-4 shrink-0"
          />
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-medium">
              {table.table_name}
            </div>
            {table.datasource_name && (
              <div className="truncate text-xs text-muted-foreground">
                {table.datasource_name}
              </div>
            )}
          </div>
          {table.fields && table.fields.length > 0 && (
            <span className="text-xs text-muted-foreground">
              {table.fields.length}
            </span>
          )}
        </Button>
      ))}
    </div>
  );
};

export default TableList;
