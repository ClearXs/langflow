import DictAreaModal from "../../../modals/dictAreaModal";

export default function ObjectRender({
  object,
  setValue,
}: {
  object: any;
  setValue?: (value: any) => void;
}): JSX.Element {
  let newObject = object;
  if (typeof object === "string") {
    try {
      newObject = JSON.parse(object);
    } catch (_e) {
      newObject = object;
    }
  }

  // Special handling for MongoDB/Neo4j format: {"value": "JSON string"}
  // Display the inner JSON string directly without re-stringifying the outer object
  let preview = "";
  if (newObject === null || newObject === undefined) {
    preview = "‎";
  } else if (
    typeof newObject === "object" &&
    Object.keys(newObject).length === 1 &&
    "value" in newObject &&
    typeof newObject.value === "string"
  ) {
    // This is the special single-field format used by MongoDB/Neo4j
    // Try to format the inner JSON string nicely
    try {
      const innerJson = JSON.parse(newObject.value);
      preview = JSON.stringify(innerJson, null, 2);
    } catch (_e) {
      // If inner value is not valid JSON, display it as-is
      preview = newObject.value;
    }
  } else {
    // Normal object - stringify it with formatting
    preview = JSON.stringify(newObject, null, 2);
  }

  return (
    <DictAreaModal onChange={setValue} value={newObject ?? {}}>
      <div className="flex h-full w-full items-center align-middle transition-all">
        <div className="truncate whitespace-pre-wrap">{preview}</div>
      </div>
    </DictAreaModal>
  );
}
