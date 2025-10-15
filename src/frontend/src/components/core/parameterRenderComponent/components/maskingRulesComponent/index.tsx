import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Plus, X, EyeOff } from 'lucide-react';
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

interface MaskingRule {
  id: string;
  field: string;
  mask_type: 'phone' | 'email' | 'id_card' | 'credit_card' | 'full' | 'hash';
  mask_char: string;
  keep_prefix: number;
  keep_suffix: number;
  enabled: boolean;
}

const MASKING_TYPES = [
  { value: 'phone', label: 'Phone Number' },
  { value: 'email', label: 'Email Address' },
  { value: 'id_card', label: 'ID Card' },
  { value: 'credit_card', label: 'Credit Card' },
  { value: 'full', label: 'Full Mask' },
  { value: 'hash', label: 'Hash' },
] as const;

export default function MaskingRulesComponent({
  value,
  handleOnNewValue,
  disabled,
  editNode = false,
  id,
}: InputProps<string | string[], any>): JSX.Element {
  const { t } = useTranslation();
  const [rules, setRules] = useState<MaskingRule[]>([]);

  useEffect(() => {
    if (!value) {
      setRules([]);
      return;
    }

    try {
      const parsed = typeof value === 'string' ? JSON.parse(value) : value;
      const rulesArray = Array.isArray(parsed) ? parsed : [];

      const formattedRules = rulesArray.map((r: any, idx: number) => ({
        id: r.id || `rule-${idx}`,
        field: r.field || '',
        mask_type: r.mask_type || 'full',
        mask_char: r.mask_char || '*',
        keep_prefix: r.keep_prefix || 0,
        keep_suffix: r.keep_suffix || 0,
        enabled: r.enabled !== undefined ? r.enabled : true,
      }));

      setRules(formattedRules);
    } catch (e) {
      setRules([]);
    }
  }, [value]);

  const updateValue = (newRules: MaskingRule[]) => {
    handleOnNewValue({ value: JSON.stringify(newRules) });
  };

  const handleAddRule = () => {
    const newRule: MaskingRule = {
      id: `rule-${Date.now()}`,
      field: '',
      mask_type: 'full',
      mask_char: '*',
      keep_prefix: 0,
      keep_suffix: 0,
      enabled: true,
    };

    const newRules = [...rules, newRule];
    setRules(newRules);
    updateValue(newRules);
  };

  const handleRemoveRule = (id: string) => {
    const newRules = rules.filter((r) => r.id !== id);
    setRules(newRules);
    updateValue(newRules);
  };

  const handleUpdateRule = (
    id: string,
    field: keyof MaskingRule,
    value: any
  ) => {
    const newRules = rules.map((r) =>
      r.id === id ? { ...r, [field]: value } : r
    );
    setRules(newRules);
    updateValue(newRules);
  };

  const isDisabled = disabled;
  const hasRules = rules.length > 0;

  return (
    <div className='w-full'>
      <div className='flex flex-col gap-3'>
        {/* Masking Rules Table */}
        {hasRules && (
          <div className='rounded-md border border-border bg-background'>
            <div className='grid grid-cols-[40px_1fr_140px_80px_80px_80px_40px] gap-2 border-b border-border bg-muted/50 p-2 text-xs font-medium'>
              <div className='flex items-center justify-center'>
                Enabled
              </div>
              <div>Field</div>
              <div>Mask Type</div>
              <div>Mask Char</div>
              <div>Keep Prefix</div>
              <div>Keep Suffix</div>
              <div></div>
            </div>

            <div className='max-h-96 overflow-y-auto'>
              {rules.map((rule) => (
                <div
                  key={rule.id}
                  className={cn(
                    'grid grid-cols-[40px_1fr_140px_80px_80px_80px_40px] gap-2 border-b border-border p-2 last:border-b-0',
                    !rule.enabled && 'opacity-50'
                  )}
                >
                  <div className='flex items-center justify-center'>
                    <Checkbox
                      checked={rule.enabled}
                      onCheckedChange={(checked) =>
                        handleUpdateRule(
                          rule.id,
                          'enabled',
                          checked as boolean
                        )
                      }
                      disabled={isDisabled}
                    />
                  </div>

                  <Input
                    value={rule.field}
                    onChange={(e) =>
                      handleUpdateRule(rule.id, 'field', e.target.value)
                    }
                    placeholder='Field name'
                    disabled={isDisabled}
                    className='h-8 text-sm'
                  />

                  <Select
                    value={rule.mask_type}
                    onValueChange={(value) =>
                      handleUpdateRule(rule.id, 'mask_type', value)
                    }
                    disabled={isDisabled}
                  >
                    <SelectTrigger className='h-8 text-sm'>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {MASKING_TYPES.map((type) => (
                        <SelectItem key={type.value} value={type.value}>
                          {type.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>

                  <Input
                    value={rule.mask_char}
                    onChange={(e) =>
                      handleUpdateRule(rule.id, 'mask_char', e.target.value)
                    }
                    placeholder='*'
                    maxLength={1}
                    disabled={isDisabled}
                    className='h-8 text-sm text-center'
                  />

                  <Input
                    type='number'
                    min='0'
                    value={rule.keep_prefix}
                    onChange={(e) =>
                      handleUpdateRule(rule.id, 'keep_prefix', parseInt(e.target.value) || 0)
                    }
                    disabled={isDisabled}
                    className='h-8 text-sm text-center'
                  />

                  <Input
                    type='number'
                    min='0'
                    value={rule.keep_suffix}
                    onChange={(e) =>
                      handleUpdateRule(rule.id, 'keep_suffix', parseInt(e.target.value) || 0)
                    }
                    disabled={isDisabled}
                    className='h-8 text-sm text-center'
                  />

                  <div className='flex items-center justify-center'>
                    {!isDisabled && (
                      <Button
                        variant='ghost'
                        size='icon'
                        className='h-8 w-8 hover:bg-destructive/10 hover:text-destructive'
                        onClick={() => handleRemoveRule(rule.id)}
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

        {/* Add Rule Button */}
        <div className='flex items-center justify-between'>
          <Button
            data-testid={`masking-rule-add-${id}`}
            disabled={isDisabled}
            variant='outline'
            size='sm'
            onClick={handleAddRule}
            className='w-full'
          >
            <Plus className='mr-2 h-4 w-4' />
            Add Masking Rule
          </Button>
        </div>

        {/* Info Text */}
        {hasRules && (
          <div className='text-xs text-muted-foreground'>
            {rules.length} masking rule{rules.length !== 1 ? 's' : ''} configured
          </div>
        )}
      </div>
    </div>
  );
}
