import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Plus, X, GitMerge } from 'lucide-react';
import { cn } from '@/utils/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import type { InputProps } from '../../types';

interface JoinCondition {
  id: string;
  left_key: string;
  right_key: string;
  enabled: boolean;
}

interface JoinConfig {
  join_type: 'inner' | 'left' | 'right' | 'outer';
  conditions: JoinCondition[];
}

const JOIN_TYPES = [
  { value: 'inner', label: 'Inner Join' },
  { value: 'left', label: 'Left Join' },
  { value: 'right', label: 'Right Join' },
  { value: 'outer', label: 'Outer Join' },
] as const;

export default function StreamJoinConfigComponent({
  value,
  handleOnNewValue,
  disabled,
  editNode = false,
  id,
}: InputProps<string | string[], any>): JSX.Element {
  const { t } = useTranslation();
  const [config, setConfig] = useState<JoinConfig>({
    join_type: 'inner',
    conditions: [],
  });

  useEffect(() => {
    if (!value) {
      setConfig({ join_type: 'inner', conditions: [] });
      return;
    }

    try {
      const parsed = typeof value === 'string' ? JSON.parse(value) : value;
      setConfig({
        join_type: parsed.join_type || 'inner',
        conditions: Array.isArray(parsed.conditions) ? parsed.conditions : [],
      });
    } catch (e) {
      setConfig({ join_type: 'inner', conditions: [] });
    }
  }, [value]);

  const updateValue = (newConfig: JoinConfig) => {
    handleOnNewValue({ value: JSON.stringify(newConfig) });
  };

  const handleAddCondition = () => {
    const newCondition: JoinCondition = {
      id: `condition-${Date.now()}`,
      left_key: '',
      right_key: '',
      enabled: true,
    };

    const newConfig = {
      ...config,
      conditions: [...config.conditions, newCondition],
    };
    setConfig(newConfig);
    updateValue(newConfig);
  };

  const handleRemoveCondition = (id: string) => {
    const newConfig = {
      ...config,
      conditions: config.conditions.filter((c) => c.id !== id),
    };
    setConfig(newConfig);
    updateValue(newConfig);
  };

  const handleUpdateCondition = (
    id: string,
    field: keyof JoinCondition,
    value: any
  ) => {
    const newConfig = {
      ...config,
      conditions: config.conditions.map((c) =>
        c.id === id ? { ...c, [field]: value } : c
      ),
    };
    setConfig(newConfig);
    updateValue(newConfig);
  };

  const handleJoinTypeChange = (joinType: string) => {
    const newConfig = {
      ...config,
      join_type: joinType as JoinConfig['join_type'],
    };
    setConfig(newConfig);
    updateValue(newConfig);
  };

  const isDisabled = disabled;
  const hasConditions = config.conditions.length > 0;

  return (
    <div className='w-full'>
      <div className='flex flex-col gap-3'>
        {/* Join Type Selection */}
        <div className='rounded-md border border-border bg-background p-3'>
          <label className='mb-2 block text-sm font-medium'>
            Join Type
          </label>
          <Select
            value={config.join_type}
            onValueChange={handleJoinTypeChange}
            disabled={isDisabled}
          >
            <SelectTrigger className='h-9'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {JOIN_TYPES.map((type) => (
                <SelectItem key={type.value} value={type.value}>
                  {type.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Join Conditions Table */}
        {hasConditions && (
          <div className='rounded-md border border-border bg-background'>
            <div className='grid grid-cols-[40px_1fr_40px_1fr_40px] gap-2 border-b border-border bg-muted/50 p-2 text-xs font-medium'>
              <div className='flex items-center justify-center'>
                Enabled
              </div>
              <div>Left Key</div>
              <div className='flex items-center justify-center'>
                <GitMerge className='h-4 w-4' />
              </div>
              <div>Right Key</div>
              <div></div>
            </div>

            <div className='max-h-96 overflow-y-auto'>
              {config.conditions.map((condition) => (
                <div
                  key={condition.id}
                  className={cn(
                    'grid grid-cols-[40px_1fr_40px_1fr_40px] gap-2 border-b border-border p-2 last:border-b-0',
                    !condition.enabled && 'opacity-50'
                  )}
                >
                  <div className='flex items-center justify-center'>
                    <Checkbox
                      checked={condition.enabled}
                      onCheckedChange={(checked) =>
                        handleUpdateCondition(
                          condition.id,
                          'enabled',
                          checked as boolean
                        )
                      }
                      disabled={isDisabled}
                    />
                  </div>

                  <Input
                    value={condition.left_key}
                    onChange={(e) =>
                      handleUpdateCondition(condition.id, 'left_key', e.target.value)
                    }
                    placeholder='Left stream key'
                    disabled={isDisabled}
                    className='h-8 text-sm'
                  />

                  <div className='flex items-center justify-center text-muted-foreground'>
                    <GitMerge className='h-4 w-4' />
                  </div>

                  <Input
                    value={condition.right_key}
                    onChange={(e) =>
                      handleUpdateCondition(condition.id, 'right_key', e.target.value)
                    }
                    placeholder='Right stream key'
                    disabled={isDisabled}
                    className='h-8 text-sm'
                  />

                  <div className='flex items-center justify-center'>
                    {!isDisabled && (
                      <Button
                        variant='ghost'
                        size='icon'
                        className='h-8 w-8 hover:bg-destructive/10 hover:text-destructive'
                        onClick={() => handleRemoveCondition(condition.id)}
                      >
                        <X className='h-4 w-4' />
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Add Condition Button */}
        <div className='flex items-center justify-between'>
          <Button
            data-testid={`stream-join-add-${id}`}
            disabled={isDisabled}
            variant='outline'
            size='sm'
            onClick={handleAddCondition}
            className='w-full'
          >
            <Plus className='mr-2 h-4 w-4' />
            Add Join Condition
          </Button>
        </div>

        {/* Info Text */}
        {hasConditions && (
          <div className='text-xs text-muted-foreground'>
            {config.conditions.length} condition{config.conditions.length !== 1 ? 's' : ''} configured
          </div>
        )}
      </div>
    </div>
  );
}
