import { useMemo } from "react";
import sortFields from "@/CustomNodes/utils/sort-fields";
import type { APIClassType } from "../../../types/api";

const useRowData = (nodeClass: APIClassType, open: boolean) => {
  const rowData = useMemo(() => {
    // Only show code field for custom components (CustomComponent or custom_components)
    const isCustomComponent =
      nodeClass.type === "CustomComponent" ||
      nodeClass.type === "custom_components";

    return Object.keys(nodeClass.template)
      .filter((key: string) => {
        const templateParam = nodeClass.template[key] as any;

        // Filter out code field for built-in components to improve performance
        if (
          !isCustomComponent &&
          key === "code" &&
          templateParam.type === "code"
        ) {
          return false;
        }

        return (
          key.charAt(0) !== "_" &&
          templateParam.show &&
          !(
            (key === "code" && templateParam.type === "code") ||
            (key.includes("code") && templateParam.proxy)
          )
        );
      })
      .sort((a, b) => sortFields(a, b, nodeClass.field_order ?? []))
      .map((key: string) => {
        const templateParam = nodeClass.template[key] as any;
        return {
          ...templateParam,
          key: key,
          id: key,
        };
      });
  }, [open, nodeClass]);

  return rowData;
};

export default useRowData;
