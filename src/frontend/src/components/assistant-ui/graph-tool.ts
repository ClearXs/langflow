export interface GraphToolInfo {
  answer: string;
  sources?: {
    entity_ids?: number[];
    document_ids?: number[];
    chunk_ids?: number[];
    paths?: Array<{
      source_entity_id: number;
      target_entity_id: number;
      relation_type: string;
      document_id?: number | null;
      chunk_id?: number | null;
      weight?: number | null;
    }>;
  };
  validation?: {
    status?: string;
    matched_doc_ids?: number[];
    chunk_doc_ids?: number[];
  };
}

function parseMetadataJson(raw: string): Record<string, unknown> | null {
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function parseGraphToolResult(
  toolName: string,
  result: unknown,
): GraphToolInfo | null {
  if (toolName !== "search_knowledge_base") return null;
  if (typeof result !== "string" || !result.trim()) return null;

  try {
    const wrapped = `<documents>${result}</documents>`;
    const parser = new DOMParser();
    const doc = parser.parseFromString(wrapped, "text/xml");

    if (doc.getElementsByTagName("parsererror").length > 0) {
      return null;
    }

    const documents = Array.from(doc.getElementsByTagName("document"));
    for (const documentEl of documents) {
      const typeEl = documentEl.querySelector("document_metadata > document_type");
      const docType = typeEl?.textContent?.trim();
      if (docType !== "KNOWLEDGE_GRAPH") continue;

      const metaEl = documentEl.querySelector("metadata_json");
      const metaRaw = metaEl?.textContent || "";
      const meta = parseMetadataJson(metaRaw);

      const chunkEl = documentEl.querySelector("document_content > chunk");
      const answer = (chunkEl?.textContent || "").trim();

      if (!answer) return null;

      return {
        answer,
        sources: (meta?.graph_sources as GraphToolInfo["sources"]) || undefined,
        validation: (meta?.graph_validation as GraphToolInfo["validation"]) || undefined,
      };
    }
  } catch {
    return null;
  }

  return null;
}
