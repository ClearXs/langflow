// Notes API Type Definitions (using Document model with NOTE type)

import type { DocumentRead } from "./documents";

export interface CreateNoteRequest {
  title: string;
  blocknote_document?: Array<Record<string, any>> | null;
}

export interface DeleteNoteResponse {
  message: string;
  note_id: number;
}

// Re-export DocumentRead as NoteRead for semantic clarity
export type NoteRead = DocumentRead;
