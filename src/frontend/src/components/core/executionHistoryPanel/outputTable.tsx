import TableComponent from "@/components/core/parameterRenderComponent/components/tableComponent";

interface OutputTableProps {
  columns: any[];
  rows: any[];
}

export default function OutputTable({ columns, rows }: OutputTableProps) {
  return (
    <div className="h-full w-full min-h-0 flex flex-col">
      <TableComponent
        columnDefs={columns}
        rowData={rows}
        onCheckboxChange={() => {}}
        pagination={rows.length > 50}
        domLayout="normal"
        className="ag-theme-shadcn h-full"
      />
    </div>
  );
}
