import { FolderPlus, Upload, Download, Trash2, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useState } from "react";
import { cn } from "@/utils/utils";
import type { FileItem } from "../types";

interface NavBarProps {
  searchQuery?: string;
  selectedFile?: FileItem | null;
  selectList?: FileItem[];
  onCreate?: () => void;
  onUpload?: () => void;
  onUploadFolder?: () => void;
  onSearch?: (query: string) => void;
  onDownload?: () => void;
  onBatchDelete?: () => void;
}

export function NavBar({
  searchQuery = "",
  selectedFile,
  selectList = [],
  onCreate,
  onUpload,
  onUploadFolder,
  onSearch,
  onDownload,
  onBatchDelete,
}: NavBarProps) {
  const [query, setQuery] = useState(searchQuery);
  const hasSelection = selectList.length > 0;

  const handleSearchInput = (value: string) => {
    setQuery(value);
    if (value === "") {
      onSearch?.("");
    }
  };

  const handleSearch = () => {
    onSearch?.(query);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  return (
    <div className="flex items-center justify-between border-b bg-background px-4 py-3">
      <div className="flex items-center gap-2">
        {/* FIXED: Always render all buttons, use CSS to hide/show - prevents flickering */}
        <div className={cn("flex items-center gap-2", hasSelection && "hidden")}>
          <Button onClick={onCreate} variant="default">
            <FolderPlus className="mr-2 h-4 w-4" />
            新建文件夹
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="default">
                <Upload className="mr-2 h-4 w-4" />
                上传
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem onClick={onUpload}>
                <Upload className="mr-2 h-4 w-4" />
                上传文件
              </DropdownMenuItem>
              <DropdownMenuItem onClick={onUploadFolder}>
                <FolderPlus className="mr-2 h-4 w-4" />
                上传文件夹
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        <div className={cn("flex items-center gap-2", !hasSelection && "hidden")}>
          <Button onClick={onDownload} variant="outline">
            <Download className="mr-2 h-4 w-4" />
            下载
          </Button>
          <Button onClick={onBatchDelete} variant="outline">
            <Trash2 className="mr-2 h-4 w-4" />
            删除
          </Button>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <div className="relative w-60">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索文件"
            value={query}
            onChange={(e) => handleSearchInput(e.target.value)}
            onKeyDown={handleKeyDown}
            className="pl-8"
          />
        </div>
        <Button onClick={handleSearch} variant="outline" size="icon">
          <Search className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
