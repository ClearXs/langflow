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
  useGetGlobalVariables,
  useGetSystemVariables,
} from '@/controllers/API/queries/variables';

const VariablesButton = () => {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const { data: globalVariables } = useGetGlobalVariables();
  const { data: systemVariables } = useGetSystemVariables();

  const allVariables = [
    ...(globalVariables || []).map((v) => ({
      ...v,
      displayName: `${v.name} [${t('variable.globalTag')}]`,
      isSystem: false,
    })),
    ...(systemVariables || []).map((v) => ({
      ...v,
      displayName: `${v.name} [${t('variable.systemTag')}]`,
      displayNameTranslated: v.display_name,
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
        v.displayNameTranslated?.toLowerCase().includes(query) ||
        v.description?.toLowerCase().includes(query)
    );
  }, [allVariables, searchQuery]);

  return (
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
      <PopoverContent className='w-96 p-0' align='end'>
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
                      className='rounded px-2 py-1.5 hover:bg-accent/50 transition-colors'
                    >
                      <div className='flex items-center justify-between gap-2'>
                        {/* Left side: Variable name with badge and description */}
                        <div className='flex items-center gap-1.5 min-w-0 flex-1'>
                          <code className='text-xs font-mono font-medium text-foreground shrink-0'>
                            {variable.name}
                          </code>
                          <span className='inline-flex items-center rounded px-1.5 py-0.5 text-[9px] font-medium bg-muted text-muted-foreground shrink-0'>
                            {variable.isSystem
                              ? t('variable.systemTag')
                              : t('variable.globalTag')}
                          </span>
                          {/* Description on same line */}
                          {(variable.displayNameTranslated ||
                            variable.description) && (
                            <span className='text-[11px] text-muted-foreground truncate'>
                              {variable.displayNameTranslated ||
                                variable.description}
                            </span>
                          )}
                        </div>

                        {/* Right side: Example */}
                        {variable.example && (
                          <div className='text-[10px] font-mono text-muted-foreground/70 shrink-0'>
                            <span>{variable.example}</span>
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
  );
};

export default VariablesButton;
