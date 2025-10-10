import { useFormLocale } from "@/i18n/locale";

export const getPlaceholder = (
  disabled: boolean,
  returnMessage: string,
) => {

  const formLocale = useFormLocale()

  if (disabled) return formLocale.RECEIVING_INPUT_VALUE;

  return returnMessage || formLocale.DEFAULT_PLACEHOLDER;
};
