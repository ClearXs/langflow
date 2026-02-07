import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface PaginationControlsProps {
  pageIndex: number;
  pageSize: number;
  total: number;
  onPageSizeChange: (size: number) => void;
  onFirst: () => void;
  onPrev: () => void;
  onNext: () => void;
  onLast: () => void;
  canPrev: boolean;
  canNext: boolean;
  id?: string;
}

export function PaginationControls({
  pageIndex,
  pageSize,
  total,
  onPageSizeChange,
  onFirst,
  onPrev,
  onNext,
  onLast,
  canPrev,
  canNext,
  id,
}: PaginationControlsProps) {
  const pageStart = pageIndex * pageSize + 1;
  const pageEnd = Math.min((pageIndex + 1) * pageSize, total);
  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="flex items-center justify-between px-2 py-4">
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Rows per page</span>
          <Select
            value={String(pageSize)}
            onValueChange={(value) => onPageSizeChange(Number(value))}
          >
            <SelectTrigger className="h-8 w-[70px]">
              <SelectValue placeholder={pageSize} />
            </SelectTrigger>
            <SelectContent side="top">
              {[10, 25, 50, 100].map((size) => (
                <SelectItem key={size} value={String(size)}>
                  {size}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <span>
            {pageStart}-{pageEnd} of {total}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-1">
        <Button
          variant="outline"
          size="sm"
          onClick={onFirst}
          disabled={!canPrev}
          className="h-8 w-8 p-0"
        >
          <ChevronsLeft className="h-4 w-4" />
          <span className="sr-only">Go to first page</span>
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={onPrev}
          disabled={!canPrev}
          className="h-8 w-8 p-0"
        >
          <ChevronLeft className="h-4 w-4" />
          <span className="sr-only">Go to previous page</span>
        </Button>
        <div className="flex items-center justify-center text-sm font-medium px-3">
          Page {pageIndex + 1} of {totalPages}
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={onNext}
          disabled={!canNext}
          className="h-8 w-8 p-0"
        >
          <ChevronRight className="h-4 w-4" />
          <span className="sr-only">Go to next page</span>
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={onLast}
          disabled={!canNext}
          className="h-8 w-8 p-0"
        >
          <ChevronsRight className="h-4 w-4" />
          <span className="sr-only">Go to last page</span>
        </Button>
      </div>
    </div>
  );
}
