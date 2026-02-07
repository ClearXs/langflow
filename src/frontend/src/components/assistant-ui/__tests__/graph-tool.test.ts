import { parseGraphToolResult } from "../graph-tool";

describe("parseGraphToolResult", () => {
  it("returns null for non-knowledge tool", () => {
    expect(parseGraphToolResult("other_tool", "test")).toBeNull();
  });

  it("parses graph answer and metadata", () => {
    const input = `
<document>
<document_metadata>
  <document_id>knowledge_graph</document_id>
  <document_type>KNOWLEDGE_GRAPH</document_type>
  <title><![CDATA[Knowledge Graph Insights]]></title>
  <metadata_json><![CDATA[{"document_type":"KNOWLEDGE_GRAPH","graph_sources":{"entity_ids":[1,2],"document_ids":[10],"chunk_ids":[100],"paths":[{"source_entity_id":1,"target_entity_id":2,"relation_type":"RELATED_TO","document_id":10,"chunk_id":100,"weight":0.9}]},"graph_validation":{"status":"ok","matched_doc_ids":[10],"chunk_doc_ids":[10]}}]]></metadata_json>
</document_metadata>
<document_content>
  <chunk><![CDATA[Graph answer text]]></chunk>
</document_content>
</document>
`;

    const parsed = parseGraphToolResult("search_knowledge_base", input);
    expect(parsed?.answer).toBe("Graph answer text");
    expect(parsed?.sources?.entity_ids).toEqual([1, 2]);
    expect(parsed?.sources?.paths?.[0]?.relation_type).toBe("RELATED_TO");
    expect(parsed?.validation?.status).toBe("ok");
  });
});
