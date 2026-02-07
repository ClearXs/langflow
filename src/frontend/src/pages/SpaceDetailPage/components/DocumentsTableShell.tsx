"use client";

import { motion } from "framer-motion";
import { ChevronDown, ChevronUp, FileX, Plus } from "lucide-react";
import React from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { DocumentTypeChip, getDocumentTypeIcon } from "./DocumentTypeIcon";
import { RowActions } from "./RowActions";
import type { ColumnVisibility, Document, SortKey } from "./types";

function sortDocuments(
  docs: Document[],
  key: SortKey,
  desc: boolean,
): Document[] {
  const sorted = [...docs].sort((a, b) => {
    const av = a[key] ?? "";
    const bv = b[key] ?? "";
    if (key === "created_at")
      return (
        new Date(av as string).getTime() - new Date(bv as string).getTime()
      );
    return String(av).localeCompare(String(bv));
  });
  return desc ? sorted.reverse() : sorted;
}

function truncate(text: string, len = 150): string {
  const plain = text
    .replace(/[#*_`>\-[\]()]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  if (plain.length <= len) return plain;
  return `${plain.slice(0, len)}...`;
}

interface DocumentsTableShellProps {
  documents: Document[];
  loading: boolean;
  error: boolean;
  onRefresh: () => Promise<void>;
  selectedIds: Set<number>;
  setSelectedIds: (update: Set<number>) => void;
  columnVisibility: ColumnVisibility;
  deleteDocument: (id: number) => Promise<boolean>;
  sortKey: SortKey;
  sortDesc: boolean;
  onSortChange: (key: SortKey) => void;
  onAddSources?: () => void;
}

export function DocumentsTableShell({
  documents,
  loading,
  error,
  onRefresh,
  selectedIds,
  setSelectedIds,
  columnVisibility,
  deleteDocument,
  sortKey,
  sortDesc,
  onSortChange,
  onAddSources,
}: DocumentsTableShellProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const params = useParams();
  const spaceId = params.spaceId;

  const sorted = React.useMemo(
    () => sortDocuments(documents, sortKey, sortDesc),
    [documents, sortKey, sortDesc],
  );

  const allSelectedOnPage =
    sorted.length > 0 && sorted.every((d) => selectedIds.has(d.id));
  const someSelectedOnPage =
    sorted.some((d) => selectedIds.has(d.id)) && !allSelectedOnPage;

  const toggleAll = (checked: boolean) => {
    const next = new Set(selectedIds);
    if (checked) sorted.forEach((d) => next.add(d.id));
    else sorted.forEach((d) => next.delete(d.id));
    setSelectedIds(next);
  };

  const toggleOne = (id: number, checked: boolean) => {
    const next = new Set(selectedIds);
    if (checked) next.add(id);
    else next.delete(id);
    setSelectedIds(next);
  };

  const onSortHeader = (key: SortKey) => onSortChange(key);

  return (
    <motion.div
      className="rounded-md border mt-6 overflow-hidden"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 300, damping: 30, delay: 0.2 }}
    >
      {loading ? (
        <div className="flex h-[400px] w-full items-center justify-center">
          <div className="flex flex-col items-center gap-2">
            <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-primary"></div>
            <p className="text-sm text-muted-foreground">
              {t("spaces.documents.loading")}
            </p>
          </div>
        </div>
      ) : error ? (
        <div className="flex h-[400px] w-full items-center justify-center">
          <div className="flex flex-col items-center gap-2">
            <p className="text-sm text-destructive">
              {t("spaces.documents.error_loading")}
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onRefresh()}
              className="mt-2"
            >
              {t("spaces.documents.retry")}
            </Button>
          </div>
        </div>
      ) : sorted.length === 0 ? (
        <div className="flex h-[400px] w-full items-center justify-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="flex flex-col items-center gap-4 max-w-md px-4 text-center"
          >
            <div className="rounded-full bg-muted p-4">
              <FileX className="h-8 w-8 text-muted-foreground" />
            </div>
            <div className="space-y-2">
              <h3 className="text-lg font-semibold">
                {t("spaces.documents.no_documents")}
              </h3>
              <p className="text-sm text-muted-foreground">
                {t("spaces.documents.get_started_by_adding")}
              </p>
            </div>
            <Button
              onClick={() => {
                if (onAddSources) {
                  onAddSources();
                } else {
                  navigate(`/spaces/${spaceId}/connectors`);
                }
              }}
              className="mt-2"
            >
              <Plus className="mr-2 h-4 w-4" />
              {t("spaces.documents.add_sources")}
            </Button>
          </motion.div>
        </div>
      ) : (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12">
                  <Checkbox
                    checked={allSelectedOnPage}
                    indeterminate={someSelectedOnPage}
                    onCheckedChange={toggleAll}
                    aria-label="Select all"
                  />
                </TableHead>
                {columnVisibility.title && (
                  <TableHead>
                    <button
                      onClick={() => onSortHeader("title")}
                      className="flex items-center gap-1 hover:text-foreground"
                    >
                      {t("spaces.documents.title")}
                      {sortKey === "title" &&
                        (sortDesc ? (
                          <ChevronDown className="h-4 w-4" />
                        ) : (
                          <ChevronUp className="h-4 w-4" />
                        ))}
                    </button>
                  </TableHead>
                )}
                {columnVisibility.doc_type && (
                  <TableHead>
                    <button
                      onClick={() => onSortHeader("doc_type")}
                      className="flex items-center gap-1 hover:text-foreground"
                    >
                      {t("spaces.documents.type")}
                      {sortKey === "doc_type" &&
                        (sortDesc ? (
                          <ChevronDown className="h-4 w-4" />
                        ) : (
                          <ChevronUp className="h-4 w-4" />
                        ))}
                    </button>
                  </TableHead>
                )}
                {columnVisibility.content && (
                  <TableHead>{t("spaces.documents.content")}</TableHead>
                )}
                {columnVisibility.created_at && (
                  <TableHead>
                    <button
                      onClick={() => onSortHeader("created_at")}
                      className="flex items-center gap-1 hover:text-foreground"
                    >
                      {t("spaces.documents.created_at")}
                      {sortKey === "created_at" &&
                        (sortDesc ? (
                          <ChevronDown className="h-4 w-4" />
                        ) : (
                          <ChevronUp className="h-4 w-4" />
                        ))}
                    </button>
                  </TableHead>
                )}
                <TableHead className="w-16">
                  {t("spaces.documents.actions")}
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sorted.map((doc) => (
                <TableRow key={doc.id}>
                  <TableCell>
                    <Checkbox
                      checked={selectedIds.has(doc.id)}
                      onCheckedChange={(checked) =>
                        toggleOne(doc.id, !!checked)
                      }
                      aria-label={`Select ${doc.title}`}
                    />
                  </TableCell>
                  {columnVisibility.title && (
                    <TableCell className="font-medium">
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <span className="cursor-pointer hover:underline">
                            {doc.title}
                          </span>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>{doc.title}</p>
                        </TooltipContent>
                      </Tooltip>
                    </TableCell>
                  )}
                  {columnVisibility.doc_type && (
                    <TableCell>
                      <DocumentTypeChip type={doc.doc_type} />
                    </TableCell>
                  )}
                  {columnVisibility.content && (
                    <TableCell className="max-w-md text-sm text-muted-foreground">
                      {doc.content ? truncate(doc.content) : "-"}
                    </TableCell>
                  )}
                  {columnVisibility.created_at && (
                    <TableCell className="text-sm text-muted-foreground">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </TableCell>
                  )}
                  <TableCell>
                    <RowActions
                      document={doc}
                      onDelete={() => deleteDocument(doc.id)}
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </>
      )}
    </motion.div>
  );
}
