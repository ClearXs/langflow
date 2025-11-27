import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import IconComponent from '@/components/common/genericIconComponent';
import GlobalVariableModal from '@/components/core/GlobalVariableModal/GlobalVariableModal';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import {
  useDeleteGlobalVariables,
  useGetGlobalVariables,
  useGetSystemVariables,
} from '@/controllers/API/queries/variables';
import useAlertStore from '@/stores/alertStore';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

const VariablesButton = () => {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [variableToDelete, setVariableToDelete] = useState<any>(null);
  const { data: globalVariables } = useGetGlobalVariables();
  const { data: systemVariables } = useGetSystemVariables();
  const { mutate: deleteVariable } = useDeleteGlobalVariables();
  const setSuccessData = useAlertStore((state) => state.setSuccessData);
  const setErrorData = useAlertStore((state) => state.setErrorData);

  const allVariables = [
    ...(globalVariables || []).map((v) => ({
      ...v,
      displayName: `${v.name} [${t('variable.globalTag')}]`,
      isSystem: false,
    })),
    ...(systemVariables || []).map((v) => ({
      ...v,
      displayName: `${v.name} [${t('variable.systemTag')}]`,
      isSystem: true,
    })),
  ];

  // Filter variables based on search query
  const filteredVariables = useMemo(() => {
    if (!searchQuery.trim()) return allVariables;

    const query = searchQuery.toLowerCase();
    return allVariables.filter(
      (v) =>
        v.name.toLowerCase().includes(query) ||
        v.displayName.toLowerCase().includes(query) ||
        v.display_name?.toLowerCase().includes(query) ||
        v.description?.toLowerCase().includes(query)
    );
  }, [allVariables, searchQuery]);

  const handleDeleteVariable = () => {
    if (!variableToDelete) return;

    deleteVariable(
      { id: variableToDelete.id },
      {
        onSuccess: () => {
          setSuccessData({
            title: t('variable.message.variableDeletedSuccessfully', {
              name: variableToDelete.name,
            }),
          });
          setDeleteDialogOpen(false);
          setVariableToDelete(null);
        },
        onError: (error: any) => {
          setErrorData({
            title: t('variable.message.errorDeletingVariable'),
            list: [
              error?.response?.data?.detail ||
                t('variable.message.unexpectedErrorDeleting'),
            ],
          });
        },
      }
    );
  };

  return (
    <>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant='ghost'
            size='icon'
            className='group flex items-center justify-center px-2 rounded-none'
            title={t('variable.variableList')}
          >
            <IconComponent
              name='Variable'
              aria-hidden='true'
              className='text-muted-foreground group-hover:text-primary !h-5 !w-5'
            />
          </Button>
        </PopoverTrigger>
        <PopoverContent className='w-84 p-0' align='end'>
          <div className='flex flex-col'>
            {/* Header with search and add button */}
            <div className='flex flex-col gap-2 px-3 pt-3 pb-2'>
              <div className='flex items-center justify-between gap-2'>
                <span className='text-sm text-muted-foreground'>
                  {t('variable.variableList')}
                </span>
              </div>
              <Input
                placeholder={t('variable.searchVariables')}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className='h-7 text-xs'
                autoComplete='off'
              />
            </div>

            <Separator />

            <GlobalVariableModal>
              <div className='mt-2 h-6 gap-1 px-1.5 text-xs hover:bg-accent justify-center flex items-center'>
                {t('variable.addVariable')}
              </div>
            </GlobalVariableModal>
            {/* Variables list */}
            <ScrollArea className='h-[300px]'>
              <div className='p-2'>
                {filteredVariables.length === 0 ? (
                  <div className='flex flex-col items-center justify-center py-6 text-muted-foreground'>
                    <IconComponent
                      name='Variable'
                      className='mb-2 h-6 w-6 opacity-50'
                    />
                    <span className='text-xs'>
                      {searchQuery
                        ? t('variable.noVariablesFound')
                        : t('variable.noVariables')}
                    </span>
                  </div>
                ) : (
                  <div className='space-y-0.5'>
                    {filteredVariables.map((variable, index) => (
                      <div
                        key={index}
                        className='rounded px-2 py-1.5 hover:bg-accent/50 transition-colors group'
                      >
                        <div className='flex items-center justify-between gap-2 w-full'>
                          {/* All variable info in one row */}
                          <div className='flex items-center gap-1.5 min-w-0 flex-1 flex-wrap'>
                            {/* Variable name */}
                            <code className='text-xs font-mono font-medium text-foreground'>
                              {variable.name}
                            </code>

                            {/* Global/System tag */}
                            <span className='inline-flex items-center rounded px-1.5 py-0.5 text-[9px] font-medium bg-muted text-muted-foreground shrink-0'>
                              {variable.isSystem
                                ? t('variable.systemTag')
                                : t('variable.globalTag')}
                            </span>

                            {/* Credential/Generic type - only for global variables */}
                            {!variable.isSystem && variable.type && (
                              <span
                                className={`inline-flex items-center rounded px-1.5 py-0.5 text-[9px] font-medium shrink-0 ${
                                  variable.type === 'Credential'
                                    ? 'bg-muted/80 text-muted-foreground/80'
                                    : 'bg-muted/60 text-muted-foreground/90'
                                }`}
                              >
                                {variable.type === 'Credential'
                                  ? t('variable.modal.credentialTab')
                                  : t('variable.modal.genericTab')}
                              </span>
                            )}

                            {/* Value or example */}
                            {!variable.isSystem && variable.value && (
                              <code className='text-[10px] font-mono text-muted-foreground/70 truncate'>
                                {variable.type === 'Credential'
                                  ? '••••••••'
                                  : variable.value}
                              </code>
                            )}
                            {variable.example && (
                              <span className='text-[10px] font-mono text-muted-foreground/70 truncate'>
                                {variable.example}
                              </span>
                            )}
                          </div>

                          {/* Action buttons - only for global variables */}
                          {!variable.isSystem && (
                            <div className='flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0'>
                              <GlobalVariableModal initialData={variable}>
                                <Button
                                  variant='ghost'
                                  size='icon'
                                  className='h-6 w-6'
                                  title={t('variable.editVariable')}
                                >
                                  <IconComponent
                                    name='Pencil'
                                    className='h-3 w-3'
                                  />
                                </Button>
                              </GlobalVariableModal>
                              <Button
                                variant='ghost'
                                size='icon'
                                className='h-6 w-6 text-destructive hover:text-destructive'
                                title={t('variable.deleteVariable')}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setVariableToDelete(variable);
                                  setDeleteDialogOpen(true);
                                }}
                              >
                                <IconComponent
                                  name='Trash2'
                                  className='h-3 w-3'
                                />
                              </Button>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </ScrollArea>
          </div>
        </PopoverContent>
      </Popover>

      {/* Delete confirmation dialog - outside Popover to prevent closing the popover */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {t('variable.deleteConfirmTitle')}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {t('variable.deleteConfirmDescription', {
                name: variableToDelete?.name,
              })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteVariable}
              className='bg-destructive text-destructive-foreground hover:bg-destructive/90'
            >
              {t('common.delete')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
};

export default VariablesButton;
