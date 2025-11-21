import { useTranslation } from "react-i18next";
import ForwardedIconComponent from "@/components/common/genericIconComponent";
import type { LineageRelationship } from "../use-get-lineage";

interface FieldMappingPanelProps {
  relationship: LineageRelationship | null;
}

const FieldMappingPanel = ({ relationship }: FieldMappingPanelProps) => {
  const { t } = useTranslation();

  if (!relationship) {
    return (
      <div className="flex h-full flex-col items-center justify-center text-sm text-muted-foreground">
        <ForwardedIconComponent name="Info" className="mb-2 h-8 w-8" />
        <p>{t("lineage.selectRelationshipHint")}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="mb-2 text-sm font-semibold">
          {t("lineage.relationship")}
        </h3>
        <div className="space-y-1 text-sm">
          <div className="flex items-center gap-2">
            <ForwardedIconComponent
              name="Database"
              className="h-4 w-4 text-blue-600"
            />
            <span className="font-medium">
              {relationship.source_table_name}
            </span>
          </div>
          <div className="ml-2 flex items-center gap-2 text-muted-foreground">
            <ForwardedIconComponent name="ArrowDown" className="h-4 w-4" />
          </div>
          <div className="flex items-center gap-2">
            <ForwardedIconComponent
              name="Database"
              className="h-4 w-4 text-green-600"
            />
            <span className="font-medium">
              {relationship.target_table_name}
            </span>
          </div>
        </div>
      </div>

      {relationship.transformation_path &&
        relationship.transformation_path.length > 0 && (
          <div>
            <h3 className="mb-2 text-sm font-semibold">
              {t("lineage.transformationPath")}
            </h3>
            <div className="space-y-1">
              {relationship.transformation_path.map((node, idx) => (
                <div key={node.id} className="flex items-center gap-2 text-sm">
                  <ForwardedIconComponent
                    name="CircleDot"
                    className="h-3 w-3 text-muted-foreground"
                  />
                  <span>{node.name}</span>
                </div>
              ))}
            </div>
          </div>
        )}

      {relationship.field_mappings &&
        relationship.field_mappings.length > 0 && (
          <div>
            <h3 className="mb-2 text-sm font-semibold">
              {t("lineage.fieldMappings")}
            </h3>
            <div className="space-y-2">
              {relationship.field_mappings.map((mapping, idx) => (
                <div
                  key={idx}
                  className="rounded-md border border-border bg-muted/30 p-2"
                >
                  <div className="mb-1 flex items-center gap-2 text-sm">
                    <span className="font-medium text-blue-600">
                      {mapping.source_field}
                    </span>
                    <ForwardedIconComponent
                      name="ArrowRight"
                      className="h-3 w-3"
                    />
                    <span className="font-medium text-green-600">
                      {mapping.target_field}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    <span>{mapping.source_type}</span>
                    <ForwardedIconComponent
                      name="ArrowRight"
                      className="h-3 w-3"
                    />
                    <span>{mapping.target_type}</span>
                  </div>
                  {mapping.transformations &&
                    mapping.transformations.length > 0 && (
                      <div className="mt-1 text-xs text-muted-foreground">
                        {t("lineage.transformations")}:{" "}
                        {mapping.transformations.join(", ")}
                      </div>
                    )}
                </div>
              ))}
            </div>
          </div>
        )}
    </div>
  );
};

export default FieldMappingPanel;
