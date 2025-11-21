export type VariableType = "Credential" | "Generic" | "system";

export type GlobalVariable = {
  id: string;
  type: VariableType;
  default_fields?: string[];
  name: string;
  value?: string;
  display_name?: string;
  display_name_en?: string;
  description?: string;
  example?: string;
};
