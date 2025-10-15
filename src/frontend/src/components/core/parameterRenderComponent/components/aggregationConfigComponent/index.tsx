import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Plus, X, Calculator } from 'lucide-react';
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

interface AggregationRule {
  id: string;
  field: string;
  function: 'sum' | 'count' | 'avg' | 'min' | 'max' | 'std' | 'median' | 'first' | 'last';
  output_name: string;
  enabled: boolean;
}

interface AggregationConfig {
  group_by_fields: string[];
  aggregations: AggregationRule[];
}

const AGGREGATION_FUNCTIONS = [
  { value: 'sum', label: 'Sum' },
  { value: 'count', label: 'Count' },
  { value: 'avg', label: 'Average' },
  { value: 'min', label: 'Minimum' },
  { value: 'max', label: 'Maximum' },
  { value: 'std', label: 'Std Dev' },
  { value: 'median', label: 'Median' },
  { value: 'first', label: 'First' },
  { value: 'last', label: 'Last' },
] as const;

export default function AggregationConfigComponent({
  value,
  handleOnNewValue,
  disabled,
  editNode = false,
  id,
}: InputProps<string | string[], any>): JSX.Element {
  const { t } = useTranslation();
  const [config, setConfig] = useState<AggregationConfig>({
    group_by_fields: [],
    aggregations: [],
  });
  const [newGroupByField, setNewGroupByField] = useState('');

  useEffect(() => {
    if (!value) {
      setConfig({ group_by_fields: [], aggregations: [] });
      return;
    }

    try {
      const parsed = typeof value === 'string' ? JSON.parse(value) : value;
      setConfig({
        group_by_fields: Array.isArray(parsed.group_by_fields) ? parsed.group_by_fields : [],
        aggregations: Array.isArray(parsed.aggregations) ? parsed.aggregations : [],
      });
    } catch (e) {
      setConfig({ group_by_fields: [], aggregations: [] });
    }
  }, [value]);

  const updateValue = (newConfig: AggregationConfig) => {
    handleOnNewValue({ value: JSON.stringify(newConfig) });
  };

  const handleAddGroupByField = () => {
    if (!newGroupByField.trim()) return;

    const newConfig = {
      ...config,
      group_by_fields: [...config.group_by_fields, newGroupByField.trim()],
    };
    setConfig(newConfig);
    updateValue(newConfig);
    setNewGroupByField('');
  };

  const handleRemoveGroupByField = (field: string) => {
    const newConfig = {
      ...config,
      group_by_fields: config.group_by_fields.filter((f) => f !== field),
    };
    setConfig(newConfig);
    updateValue(newConfig);
  };

  const handleAddAggregation = () => {
    const newAggregation: AggregationRule = {
      id: `agg-${Date.now()}`,
      field: '',
      function: 'sum',
      output_name: '',
      enabled: true,
    };

    const newConfig = {
      ...config,
      aggregations: [...config.aggregations, newAggregation],
    };
    setConfig(newConfig);
    updateValue(newConfig);
  };

  const handleRemoveAggregation = (id: string) => {
    const newConfig = {
      ...config,
      aggregations: config.aggregations.filter((a) => a.id !== id),
    };
    setConfig(newConfig);
    updateValue(newConfig);
  };

  const handleUpdateAggregation = (
    id: string,
    field: keyof AggregationRule,
    value: any
  ) => {
    const newConfig = {
      ...config,
      aggregations: config.aggregations.map((a) =>
        a.id === id ? { ...a, [field]: value } : a
      ),
    };
    setConfig(newConfig);
    updateValue(newConfig);
  };

  const isDisabled = disabled;
  const hasGroupByFields = config.group_by_fields.length > 0;
  const hasAggregations = config.aggregations.length > 0;

  return (
    <div className='w-full'>
      <div className='flex flex-col gap-3'>
        {/* Group By Fields Section */}
        <div className='rounded-md border border-border bg-background p-3'>
          <label className='mb-2 block text-sm font-medium'>
            Group By Fields
          </label>

          {/* Add Group By Field Input */}
          <div className='mb-2 flex gap-2'>
            <Input
              value={newGroupByField}
              onChange={(e) => setNewGroupByField(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  handleAddGroupByField();
                }
              }}
              placeholder='Enter field name'
              disabled={isDisabled}
              className='h-9 text-sm'
            />
            <Button
              onClick={handleAddGroupByField}
              disabled={isDisabled || !newGroupByField.trim()}
              variant='outline'
              size='sm'
            >
              <Plus className='h-4 w-4' />
            </Button>
          </div>

          {/* Group By Fields List */}
          {hasGroupByFields && (
            <div className='flex flex-wrap gap-2'>
              {config.group_by_fields.map((field) => (
                <div
                  key={field}
                  className='flex items-center gap-1 rounded-md border border-border bg-muted px-2 py-1 text-sm'
                >
                  <span>{field}</span>
                  {!isDisabled && (
                    <button
                      onClick={() => handleRemoveGroupByField(field)}
                      className='ml-1 hover:text-destructive'
                    >
                      <X className='h-3 w-3' />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Aggregation Rules Table */}
        {hasAggregations && (
          <div className='rounded-md border border-border bg-background'>
            <div className='grid grid-cols-[40px_1fr_140px_1fr_40px] gap-2 border-b border-border bg-muted/50 p-2 text-xs font-medium'>
              <div className='flex items-center justify-center'>
                Enabled
              </div>
              <div>Field</div>
              <div>Function</div>
              <div>Output Name</div>
              <div></div>
            </div>

            <div className='max-h-96 overflow-y-auto'>
              {config.aggregations.map((agg) => (
                <div
                  key={agg.id}
                  className={cn(
                    'grid grid-cols-[40px_1fr_140px_1fr_40px] gap-2 border-b border-border p-2 last:border-b-0',
                    !agg.enabled && 'opacity-50'
                  )}
                >
                  <div className='flex items-center justify-center'>
                    <Checkbox
                      checked={agg.enabled}
                      onCheckedChange={(checked) =>
                        handleUpdateAggregation(
                          agg.id,
                          'enabled',
                          checked as boolean
                        )
                      }
                      disabled={isDisabled}
                    />
                  </div>

                  <Input
                    value={agg.field}
                    onChange={(e) =>
                      handleUpdateAggregation(agg.id, 'field', e.target.value)
                    }
                    placeholder='Field name'
                    disabled={isDisabled}
                    className='h-8 text-sm'
                  />

                  <Select
                    value={agg.function}
                    onValueChange={(value) =>
                      handleUpdateAggregation(agg.id, 'function', value)
                    }
                    disabled={isDisabled}
                  >
                    <SelectTrigger className='h-8 text-sm'>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {AGGREGATION_FUNCTIONS.map((func) => (
                        <SelectItem key={func.value} value={func.value}>
                          {func.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>

                  <Input
                    value={agg.output_name}
                    onChange={(e) =>
                      handleUpdateAggregation(agg.id, 'output_name', e.target.value)
                    }
                    placeholder='Output column name'
                    disabled={isDisabled}
                    className='h-8 text-sm'
                  />

                  <div className='flex items-center justify-center'>
                    {!isDisabled && (
                      <Button
                        variant='ghost'
                        size='icon'
                        className='h-8 w-8 hover:bg-destructive/10 hover:text-destructive'
                        onClick={() => handleRemoveAggregation(agg.id)}
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

        {/* Add Aggregation Button */}
        <div className='flex items-center justify-between'>
          <Button
            data-testid={`aggregation-add-${id}`}
            disabled={isDisabled}
            variant='outline'
            size='sm'
            onClick={handleAddAggregation}
            className='w-full'
          >
            <Plus className='mr-2 h-4 w-4' />
            Add Aggregation Rule
          </Button>
        </div>

        {/* Info Text */}
        {(hasGroupByFields || hasAggregations) && (
          <div className='text-xs text-muted-foreground'>
            {config.group_by_fields.length} group by field{config.group_by_fields.length !== 1 ? 's' : ''}, {config.aggregations.length} aggregation{config.aggregations.length !== 1 ? 's' : ''}
          </div>
        )}
      </div>
    </div>
  );
}
