import { motion } from "framer-motion";
import { useCallback, useEffect, useId, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import {
  useDeleteDocument,
  useGetDocumentsQuery,
  useGetDocumentTypeCountsQuery,
  useSearchDocumentsQuery,
} from "@/controllers/API/queries/documents";
import { AddDataSourcesDialog } from "./components/AddDataSourcesDialog";
import { DocumentsFilters } from "./components/DocumentsFilters";
import { DocumentsTableShell } from "./components/DocumentsTableShell";
import { PaginationControls } from "./components/PaginationControls";
import type {
  ColumnVisibility,
  DocumentTypeEnum,
  SortKey,
} from "./components/types";

/**
 * Custom hook for debouncing a value
 */
function useDebounced<T>(value: T, delay = 250): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

export default function DocumentsPage() {
  const { t } = useTranslation();
  const id = useId();
  const { spaceId } = useParams<{ spaceId: string }>();
  const spaceIdNum = useMemo(() => Number(spaceId) || 0, [spaceId]);

  // State management
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounced(search, 250);
  const [activeTypes, setActiveTypes] = useState<DocumentTypeEnum[]>([]);
  const [columnVisibility, setColumnVisibility] = useState<ColumnVisibility>({
    title: true,
    doc_type: true,
    content: true,
    created_at: true,
  });
  const [pageIndex, setPageIndex] = useState(0);
  const [pageSize, setPageSize] = useState(50);
  const [sortKey, setSortKey] = useState<SortKey>("title");
  const [sortDesc, setSortDesc] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);

  // API queries
  const { data: typeCountsData } = useGetDocumentTypeCountsQuery(
    { enabled: !!spaceId },
    { search_space_id: spaceIdNum },
  );

  // Build query parameters for fetching documents
  const queryParams = useMemo(
    () => ({
      search_space_id: spaceIdNum,
      page: pageIndex,
      page_size: pageSize,
      ...(activeTypes.length > 0 && { document_types: activeTypes }),
    }),
    [spaceIdNum, pageIndex, pageSize, activeTypes],
  );

  // Build search query parameters
  const searchQueryParams = useMemo(
    () => ({
      search_space_id: spaceIdNum,
      page: pageIndex,
      page_size: pageSize,
      title: debouncedSearch.trim(),
      ...(activeTypes.length > 0 && { document_types: activeTypes }),
    }),
    [spaceIdNum, pageIndex, pageSize, activeTypes, debouncedSearch],
  );

  // Use query for fetching documents (when not searching)
  const {
    data: documentsResponse,
    isLoading: isDocumentsLoading,
    refetch: refetchDocuments,
    error: documentsError,
  } = useGetDocumentsQuery(
    {
      enabled: !!spaceId && !debouncedSearch.trim(),
    },
    queryParams,
  );

  // Use query for searching documents
  const {
    data: searchResponse,
    isLoading: isSearchLoading,
    refetch: refetchSearch,
    error: searchError,
  } = useSearchDocumentsQuery(
    {
      enabled: !!spaceId && !!debouncedSearch.trim(),
    },
    searchQueryParams,
  );

  const deleteDocumentMutation = useDeleteDocument();

  // Extract documents and total based on search state
  const documents = debouncedSearch.trim()
    ? searchResponse?.items || []
    : documentsResponse?.items || [];
  const total = debouncedSearch.trim()
    ? searchResponse?.total || 0
    : documentsResponse?.total || 0;
  const loading = debouncedSearch.trim() ? isSearchLoading : isDocumentsLoading;
  const error = debouncedSearch.trim() ? searchError : documentsError;

  // Type counts (convert from array to Record format expected by DocumentsFilters)
  const typeCounts = useMemo(() => {
    if (!typeCountsData) return {};
    // If it's already a Record, return as-is; otherwise convert array to Record
    if (Array.isArray(typeCountsData)) {
      return typeCountsData.reduce(
        (acc, item) => {
          acc[item.doc_type as DocumentTypeEnum] = item.count;
          return acc;
        },
        {} as Record<DocumentTypeEnum, number>,
      );
    }
    return typeCountsData as Record<DocumentTypeEnum, number>;
  }, [typeCountsData]);

  // Display documents with pagination
  const pageStart = pageIndex * pageSize;
  const pageEnd = Math.min(pageStart + pageSize, total);

  // Handlers
  const onToggleType = useCallback(
    (type: DocumentTypeEnum, checked: boolean) => {
      setActiveTypes((prev) =>
        checked ? [...prev, type] : prev.filter((t) => t !== type),
      );
      setPageIndex(0);
    },
    [],
  );

  const onToggleColumn = useCallback(
    (id: keyof ColumnVisibility, checked: boolean) => {
      setColumnVisibility((prev) => ({ ...prev, [id]: checked }));
    },
    [],
  );

  const refreshCurrentView = useCallback(async () => {
    if (debouncedSearch.trim()) {
      await refetchSearch();
    } else {
      await refetchDocuments();
    }
  }, [debouncedSearch, refetchSearch, refetchDocuments]);

  // Delete single document
  const deleteDocument = useCallback(
    async (id: number) => {
      try {
        await deleteDocumentMutation.mutateAsync({
          documentId: id,
          search_space_id: spaceIdNum,
        });
        await refreshCurrentView();
        return true;
      } catch (error) {
        console.error("Failed to delete document:", error);
        return false;
      }
    },
    [deleteDocumentMutation, refreshCurrentView, spaceIdNum],
  );

  // Bulk delete
  const onBulkDelete = useCallback(async () => {
    if (selectedIds.size === 0) {
      toast.error(t("spaces.documents.no_rows_selected"));
      return;
    }

    try {
      // Delete documents one by one
      const results = await Promise.all(
        Array.from(selectedIds).map(async (id) => {
          try {
            await deleteDocumentMutation.mutateAsync({
              documentId: id,
              search_space_id: spaceIdNum,
            });
            return true;
          } catch {
            return false;
          }
        }),
      );

      const okCount = results.filter((r) => r === true).length;
      if (okCount === selectedIds.size) {
        toast.success(t("spaces.documents.delete_success_count", { count: okCount }));
      } else {
        toast.error(t("spaces.documents.delete_partial_failed"));
      }

      // Refetch the current view
      await refreshCurrentView();
      setSelectedIds(new Set());
    } catch (e) {
      console.error(e);
      toast.error("Failed to delete documents");
    }
  }, [selectedIds, deleteDocumentMutation, refreshCurrentView, spaceIdNum]);

  // Responsive column visibility
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 768px)");
    const apply = (isSmall: boolean) => {
      setColumnVisibility((prev) => ({
        ...prev,
        content: !isSmall,
        created_at: !isSmall,
      }));
    };
    apply(mq.matches);
    const onChange = (e: MediaQueryListEvent) => apply(e.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="w-full px-6 py-4 min-h-[calc(100vh-64px)]"
    >
      <DocumentsFilters
        typeCounts={typeCounts}
        selectedIds={selectedIds}
        onSearch={setSearch}
        searchValue={search}
        onBulkDelete={onBulkDelete}
        onToggleType={onToggleType}
        activeTypes={activeTypes}
        columnVisibility={columnVisibility}
        onToggleColumn={onToggleColumn}
        onUpload={() => setUploadDialogOpen(true)}
      />

      <DocumentsTableShell
        documents={documents}
        loading={loading}
        error={!!error}
        onRefresh={refreshCurrentView}
        selectedIds={selectedIds}
        setSelectedIds={setSelectedIds}
        columnVisibility={columnVisibility}
        deleteDocument={deleteDocument}
        sortKey={sortKey}
        sortDesc={sortDesc}
        onSortChange={(key) => {
          if (sortKey === key) setSortDesc((v) => !v);
          else {
            setSortKey(key);
            setSortDesc(false);
          }
        }}
        onAddSources={() => setUploadDialogOpen(true)}
      />

      <PaginationControls
        pageIndex={pageIndex}
        pageSize={pageSize}
        total={total}
        onPageSizeChange={(size) => {
          setPageSize(size);
          setPageIndex(0);
        }}
        onFirst={() => setPageIndex(0)}
        onPrev={() => setPageIndex((i) => Math.max(0, i - 1))}
        onNext={() => setPageIndex((i) => (pageEnd < total ? i + 1 : i))}
        onLast={() =>
          setPageIndex(Math.max(0, Math.ceil(total / pageSize) - 1))
        }
        canPrev={pageIndex > 0}
        canNext={pageEnd < total}
        id={id}
      />

      <AddDataSourcesDialog
        open={uploadDialogOpen}
        onOpenChange={setUploadDialogOpen}
        spaceId={spaceIdNum}
        onUploadSuccess={refreshCurrentView}
      />
    </motion.div>
  );
}
