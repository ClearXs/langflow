import type { CustomCellRendererProps } from "ag-grid-react";
import { BracesIcon } from "lucide-react";
import { uniqueId } from "lodash";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import NumberReader from "@/components/common/numberReader";
import ObjectRender from "@/components/common/objectRender";
import StringReader from "@/components/common/stringReaderComponent";
import DateReader from "@/components/core/dateReaderComponent";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn, isTimeStampString } from "@/utils/utils";
import InputGlobalComponent from "../../../inputGlobalComponent";
import ToggleShadComponent from "../../../toggleShadComponent";

interface JsonData {
  _type?: string;
  formatted: string;
  raw: any;
  preview: string;
}

function JsonDataDialog({ jsonData }: { jsonData: JsonData }) {
  const [open, setOpen] = useState(false);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <div
          className="flex cursor-pointer items-center gap-2 overflow-hidden rounded px-2 py-1 hover:bg-muted"
          onClick={() => setOpen(true)}
        >
          <BracesIcon className="h-4 w-4 flex-shrink-0 text-blue-500" />
          <span className="truncate text-sm text-muted-foreground">
            {jsonData.preview}
          </span>
        </div>
      </DialogTrigger>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>JSON Data</DialogTitle>
        </DialogHeader>
        <div className="max-h-[60vh] overflow-auto">
          <pre className="rounded bg-secondary p-4 text-xs text-secondary-foreground">
            {jsonData.formatted}
          </pre>
        </div>
      </DialogContent>
    </Dialog>
  );
}

interface CustomCellRender extends CustomCellRendererProps {
  formatter?:
    | "json"
    | "text"
    | "boolean"
    | "number"
    | "undefined"
    | "null"
    | "geometry";
}

export default function TableAutoCellRender({
  value,
  setValue,
  colDef,
  formatter,
  api,
  ...props
}: CustomCellRender) {
  const { t } = useTranslation();

  // Try to translate value for known patterns (data types and transformation rules)
  const getTranslatedValue = (val: string) => {
    if (typeof val !== "string") return val;

    // Check if it's a data type
    const dataTypeKey = `dataTypes.${val}`;
    const dataTypeTranslation = t(dataTypeKey);
    if (dataTypeTranslation !== dataTypeKey) {
      return dataTypeTranslation;
    }

    // Check if it's a transformation rule
    const transformKey = `transformation.rules.${val}`;
    const transformTranslation = t(transformKey);
    if (transformTranslation !== transformKey) {
      return transformTranslation;
    }

    // Return original if no translation found
    return val;
  };

  function getCellType() {
    // Helper function to check if a string is valid JSON
    const isValidJSON = (str: string): boolean => {
      if (typeof str !== "string") return false;
      try {
        const parsed = JSON.parse(str);
        return typeof parsed === "object" && parsed !== null;
      } catch {
        return false;
      }
    };

    // Helper function to parse and format JSON
    const parseJSON = (str: string) => {
      try {
        const parsed = JSON.parse(str);
        return {
          raw: parsed,
          formatted: JSON.stringify(parsed, null, 2),
          preview:
            str.length > 100 ? str.substring(0, 100) + "..." : str,
        };
      } catch {
        return null;
      }
    };

    // Check if value is JSON metadata from backend (preferred format)
    const isJsonMetadata =
      value &&
      typeof value === "object" &&
      value !== null &&
      value._type === "json" &&
      "formatted" in value &&
      "preview" in value;

    // If it's our special JSON metadata format, render with clickable icon and dialog
    if (isJsonMetadata) {
      return <JsonDataDialog jsonData={value} />;
    }

    // Check if value is a JSON string (but not our metadata format)
    if (typeof value === "string" && isValidJSON(value)) {
      const jsonData = parseJSON(value);
      if (jsonData) {
        return <JsonDataDialog jsonData={jsonData} />;
      }
    }

    let format: string = formatter ? formatter : typeof value;
    //convert text to string to bind to the string reader
    format = format === "text" ? "string" : format;
    format = format === "json" ? "object" : format;

    // Handle geometry/spatial types - convert GeoJSON object to string
    // Check both formatter and if value is a GeoJSON-like object
    const isGeoJSON =
      (format === "geometry" && typeof value === "object" && value !== null) ||
      (typeof value === "object" &&
        value !== null &&
        "type" in value &&
        "coordinates" in value);

    if (isGeoJSON) {
      const geoJsonString = JSON.stringify(value, null, 2); // Pretty print with 2 spaces
      return (
        <StringReader
          editable={
            !!colDef?.onCellValueChanged ||
            !!api.getGridOption("onCellValueChanged")
          }
          setValue={(newValue) => {
            try {
              // Parse back to object when editing
              const parsed = JSON.parse(newValue);
              setValue?.(parsed);
            } catch {
              // If invalid JSON, keep as is
              setValue?.(newValue);
            }
          }}
          string={geoJsonString}
        />
      );
    }

    switch (format) {
      case "object":
        return (
          <ObjectRender
            setValue={colDef?.onCellValueChanged ? setValue : undefined}
            object={value}
          />
        );

      case "string": {
        // Translate the value if applicable
        const translatedValue = getTranslatedValue(value);

        if (isTimeStampString(value)) {
          return <DateReader date={value} />;
        }
        //TODO: REFACTOR FOR ANY LABEL NOT HARDCODED
        else if (value === "success") {
          return (
            <Badge
              variant="successStatic"
              size="sq"
              className={cn("h-[18px] w-full justify-center")}
            >
              {value}
            </Badge>
          );
        } else if (value === "failure") {
          return (
            <Badge
              variant="errorStatic"
              size="sq"
              className={cn("h-[18px] w-full justify-center")}
            >
              {value}
            </Badge>
          );
        } else if (colDef?.context?.globalVariable) {
          return (
            <InputGlobalComponent
              id="string-reader-global"
              value={value ?? ""}
              editNode={false}
              handleOnNewValue={(newValue) => {
                setValue?.(newValue.value);
              }}
              disabled={
                !colDef?.onCellValueChanged &&
                !api.getGridOption("onCellValueChanged")
              }
              load_from_db={true}
              allowCustomValue={false}
              password={false}
              display_name=""
              placeholder=""
              isToolMode={false}
              hasRefreshButton={false}
            />
          );
        } else {
          return (
            <StringReader
              editable={
                !!colDef?.onCellValueChanged ||
                !!api.getGridOption("onCellValueChanged")
              }
              setValue={setValue!}
              string={translatedValue}
            />
          );
        }
      }
      case "number":
        return <NumberReader number={value} />;
      case "undefined":
        return "";
      case "null":
        return "";
      case "boolean":
        value =
          (typeof value === "string" && value.toLowerCase() === "true") ||
          value === true
            ? true
            : false;
        return !!colDef?.onCellValueChanged ||
          !!api.getGridOption("onCellValueChanged") ? (
          <ToggleShadComponent
            value={value}
            handleOnNewValue={(data) => {
              setValue?.(data.value);
            }}
            editNode={true}
            id={"toggle" + colDef?.colId + uniqueId()}
            disabled={
              colDef?.cellRendererParams?.isSingleToggleColumn &&
              colDef?.cellRendererParams?.checkSingleToggleEditable
                ? !colDef.cellRendererParams.checkSingleToggleEditable(props)
                : false
            }
          />
        ) : (
          <Badge
            variant={value ? "successStatic" : "errorStatic"}
            size="sq"
            className="h-[18px]"
          >
            {String(value).toLowerCase()}
          </Badge>
        );
      default:
        return String(value);
    }
  }

  return (
    <div className="group flex h-full w-full items-center truncate text-align-last-left">
      {getCellType()}
    </div>
  );
}
