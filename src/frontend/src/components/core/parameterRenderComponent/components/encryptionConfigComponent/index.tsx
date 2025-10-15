import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Plus, X, Lock, Eye, EyeOff } from 'lucide-react';
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
import type { InputProps } from '../../types';

interface EncryptionConfig {
  operation: 'encrypt' | 'decrypt';
  algorithm: 'fernet' | 'aes-256-cbc' | 'aes-128-cbc';
  key: string;
  fields: string[];
}

const OPERATIONS = [
  { value: 'encrypt', label: 'Encrypt' },
  { value: 'decrypt', label: 'Decrypt' },
] as const;

const ALGORITHMS = [
  { value: 'fernet', label: 'Fernet (Symmetric)' },
  { value: 'aes-256-cbc', label: 'AES-256-CBC' },
  { value: 'aes-128-cbc', label: 'AES-128-CBC' },
] as const;

export default function EncryptionConfigComponent({
  value,
  handleOnNewValue,
  disabled,
  editNode = false,
  id,
}: InputProps<string | string[], any>): JSX.Element {
  const { t } = useTranslation();
  const [config, setConfig] = useState<EncryptionConfig>({
    operation: 'encrypt',
    algorithm: 'fernet',
    key: '',
    fields: [],
  });
  const [showKey, setShowKey] = useState(false);
  const [newField, setNewField] = useState('');

  useEffect(() => {
    if (!value) {
      setConfig({
        operation: 'encrypt',
        algorithm: 'fernet',
        key: '',
        fields: [],
      });
      return;
    }

    try {
      const parsed = typeof value === 'string' ? JSON.parse(value) : value;
      setConfig({
        operation: parsed.operation || 'encrypt',
        algorithm: parsed.algorithm || 'fernet',
        key: parsed.key || '',
        fields: Array.isArray(parsed.fields) ? parsed.fields : [],
      });
    } catch (e) {
      setConfig({
        operation: 'encrypt',
        algorithm: 'fernet',
        key: '',
        fields: [],
      });
    }
  }, [value]);

  const updateValue = (newConfig: EncryptionConfig) => {
    handleOnNewValue({ value: JSON.stringify(newConfig) });
  };

  const handleOperationChange = (operation: string) => {
    const newConfig = {
      ...config,
      operation: operation as EncryptionConfig['operation'],
    };
    setConfig(newConfig);
    updateValue(newConfig);
  };

  const handleAlgorithmChange = (algorithm: string) => {
    const newConfig = {
      ...config,
      algorithm: algorithm as EncryptionConfig['algorithm'],
    };
    setConfig(newConfig);
    updateValue(newConfig);
  };

  const handleKeyChange = (key: string) => {
    const newConfig = {
      ...config,
      key,
    };
    setConfig(newConfig);
    updateValue(newConfig);
  };

  const handleAddField = () => {
    if (!newField.trim()) return;

    const newConfig = {
      ...config,
      fields: [...config.fields, newField.trim()],
    };
    setConfig(newConfig);
    updateValue(newConfig);
    setNewField('');
  };

  const handleRemoveField = (field: string) => {
    const newConfig = {
      ...config,
      fields: config.fields.filter((f) => f !== field),
    };
    setConfig(newConfig);
    updateValue(newConfig);
  };

  const isDisabled = disabled;
  const hasFields = config.fields.length > 0;

  return (
    <div className='w-full'>
      <div className='flex flex-col gap-3'>
        {/* Operation Type */}
        <div className='rounded-md border border-border bg-background p-3'>
          <label className='mb-2 block text-sm font-medium'>
            Operation
          </label>
          <Select
            value={config.operation}
            onValueChange={handleOperationChange}
            disabled={isDisabled}
          >
            <SelectTrigger className='h-9'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {OPERATIONS.map((op) => (
                <SelectItem key={op.value} value={op.value}>
                  {op.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Algorithm Selection */}
        <div className='rounded-md border border-border bg-background p-3'>
          <label className='mb-2 block text-sm font-medium'>
            Algorithm
          </label>
          <Select
            value={config.algorithm}
            onValueChange={handleAlgorithmChange}
            disabled={isDisabled}
          >
            <SelectTrigger className='h-9'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {ALGORITHMS.map((alg) => (
                <SelectItem key={alg.value} value={alg.value}>
                  {alg.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Encryption Key */}
        <div className='rounded-md border border-border bg-background p-3'>
          <label className='mb-2 block text-sm font-medium'>
            Encryption Key
          </label>
          <div className='relative'>
            <Input
              type={showKey ? 'text' : 'password'}
              value={config.key}
              onChange={(e) => handleKeyChange(e.target.value)}
              placeholder='Enter encryption key'
              disabled={isDisabled}
              className='h-9 pr-10 text-sm'
            />
            <button
              type='button'
              onClick={() => setShowKey(!showKey)}
              className='absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground'
              disabled={isDisabled}
            >
              {showKey ? (
                <EyeOff className='h-4 w-4' />
              ) : (
                <Eye className='h-4 w-4' />
              )}
            </button>
          </div>
        </div>

        {/* Fields to Encrypt/Decrypt */}
        <div className='rounded-md border border-border bg-background p-3'>
          <label className='mb-2 block text-sm font-medium'>
            Fields to {config.operation === 'encrypt' ? 'Encrypt' : 'Decrypt'}
          </label>

          {/* Add Field Input */}
          <div className='mb-2 flex gap-2'>
            <Input
              value={newField}
              onChange={(e) => setNewField(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  handleAddField();
                }
              }}
              placeholder='Enter field name'
              disabled={isDisabled}
              className='h-9 text-sm'
            />
            <Button
              onClick={handleAddField}
              disabled={isDisabled || !newField.trim()}
              variant='outline'
              size='sm'
            >
              <Plus className='h-4 w-4' />
            </Button>
          </div>

          {/* Fields List */}
          {hasFields && (
            <div className='flex flex-wrap gap-2'>
              {config.fields.map((field) => (
                <div
                  key={field}
                  className='flex items-center gap-1 rounded-md border border-border bg-muted px-2 py-1 text-sm'
                >
                  <Lock className='h-3 w-3' />
                  <span>{field}</span>
                  {!isDisabled && (
                    <button
                      onClick={() => handleRemoveField(field)}
                      className='ml-1 hover:text-destructive'
                    >
                      <X className='h-3 w-3' />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}

          {!hasFields && (
            <div className='text-xs text-muted-foreground italic'>
              No fields selected. Add field names to {config.operation}.
            </div>
          )}
        </div>

        {/* Info Text */}
        {hasFields && (
          <div className='text-xs text-muted-foreground'>
            {config.fields.length} field{config.fields.length !== 1 ? 's' : ''} will be {config.operation === 'encrypt' ? 'encrypted' : 'decrypted'} using {config.algorithm.toUpperCase()}
          </div>
        )}
      </div>
    </div>
  );
}
