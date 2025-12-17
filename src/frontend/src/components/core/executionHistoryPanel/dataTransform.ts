export interface TableData {
  columns: any[];
  rows: any[];
}

export function transformOutputData(data: any): TableData {
  // JSON Array: 直接展示
  if (Array.isArray(data)) {
    if (data.length === 0) {
      return { columns: [], rows: [] };
    }

    // 自动提取列（使用第一个对象的 keys）
    const firstItem = data[0];
    if (typeof firstItem === "object" && firstItem !== null) {
      const columns = Object.keys(firstItem).map((key) => ({
        headerName: key.replace(/_/g, " "),
        field: key,
        minWidth: 150,
        flex: 1,
        resizable: true,
        wrapText: true,
        autoHeight: true,
        cellRenderer: (params: any) => {
          const value = params.value;
          if (value === null || value === undefined) {
            return "(null)";
          }
          if (typeof value === "object" && value !== null) {
            return JSON.stringify(value, null, 2);
          }
          return String(value);
        },
      }));
      return { columns, rows: data };
    }

    // 基础类型数组
    const columns = [{ headerName: "Value", field: "value", flex: 1 }];
    const rows = data.map((item) => ({ value: item }));
    return { columns, rows };
  }

  // JSON Object: 转换为 key-value 对的数组以便更好地展示
  if (typeof data === "object" && data !== null) {
    // 将对象转换为键值对数组
    const rows = Object.entries(data).map(([key, value]) => ({
      field: key,
      value:
        typeof value === "object" && value !== null
          ? JSON.stringify(value, null, 2)
          : value === null || value === undefined
            ? "(null)"
            : String(value),
    }));

    const columns = [
      {
        headerName: "Field",
        field: "field",
        minWidth: 200,
        width: 250,
        resizable: true,
        cellStyle: { fontWeight: "bold" },
      },
      {
        headerName: "Value",
        field: "value",
        minWidth: 400,
        flex: 1,
        resizable: true,
        autoHeight: true,
        wrapText: true,
        cellStyle: { whiteSpace: "pre-wrap" },
      },
    ];

    return { columns, rows };
  }

  // 基础类型: 简单包装
  return {
    columns: [{ headerName: "Value", field: "value", flex: 1 }],
    rows: [{ value: String(data) }],
  };
}
