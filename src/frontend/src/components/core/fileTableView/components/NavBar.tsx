import { Download, FolderPlus, Search, Trash2, Upload } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Input } from '@/components/ui/input';
import type { FileItem } from '../types';

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
  searchQuery = '',
  selectedFile,
  selectList = [],
  onCreate,
  onUpload,
  onUploadFolder,
  onSearch,
  onDownload,
  onBatchDelete,
}: NavBarProps) {
  const { t } = useTranslation();
  const [query, setQuery] = useState(searchQuery);
  const hasSelection = selectList.length > 0;

  // Sync external searchQuery to internal state
  useEffect(() => {
    setQuery(searchQuery);
  }, [searchQuery]);

  const handleSearchInput = (value: string) => {
    setQuery(value);
    if (value === '') {
      onSearch?.('');
    }
  };

  const handleSearch = () => {
    onSearch?.(query);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <div className='flex items-center justify-between border-b bg-background px-4 py-3'>
      <div className='flex items-center gap-2 relative min-h-[36px]'>
        {/* Create/Upload buttons - shown when no selection and callbacks provided */}
        {!hasSelection && (onCreate || onUpload) && (
          <div className='flex items-center gap-2'>
            {onCreate && (
              <Button onClick={onCreate} variant='default' size='sm'>
                <FolderPlus className='mr-2 h-4 w-4' />
                {t('fileTableModal.newFolder')}
              </Button>
            )}

            {onUpload && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant='default' size='sm'>
                    <Upload className='mr-2 h-4 w-4' />
                    {t('fileTableModal.upload')}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem onClick={onUpload}>
                    <Upload className='mr-2 h-4 w-4' />
                    {t('fileTableModal.uploadFile')}
                  </DropdownMenuItem>
                  {onUploadFolder && (
                    <DropdownMenuItem onClick={onUploadFolder}>
                      <FolderPlus className='mr-2 h-4 w-4' />
                      {t('fileTableModal.uploadFolder')}
                    </DropdownMenuItem>
                  )}
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>
        )}

        {/* Download/Delete buttons - shown when has selection and callbacks provided */}
        {hasSelection && (onDownload || onBatchDelete) && (
          <div className='flex items-center gap-2'>
            {onDownload && (
              <Button onClick={onDownload} variant='outline' size='sm'>
                <Download className='mr-2 h-4 w-4' />
                {t('fileTableModal.download')}
              </Button>
            )}
            {onBatchDelete && (
              <Button onClick={onBatchDelete} variant='outline' size='sm'>
                <Trash2 className='mr-2 h-4 w-4' />
                {t('fileTableModal.delete')}
              </Button>
            )}
          </div>
        )}
      </div>

      <div className='flex items-center gap-2'>
        <div className='relative w-60'>
          <Input
            type='search'
            placeholder={t('fileTableModal.searchFiles')}
            value={query}
            onChange={(e) => handleSearchInput(e.target.value)}
            onKeyDown={handleKeyDown}
            autoComplete='off'
          />
        </div>
        <Button
          onClick={handleSearch}
          variant='outline'
          size='sm'
          className='h-9 w-9 p-0'
        >
          <Search className='h-4 w-4' />
        </Button>
      </div>
    </div>
  );
}
