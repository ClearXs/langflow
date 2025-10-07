import type { UseMutationResult } from "@tanstack/react-query";
import type { useMutationFunctionType } from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";
import { Language } from "@/types/zustand/i18n";

interface ISwitchLocale {
  lang: Language;
}

export const useSwitchLocale: useMutationFunctionType<
  undefined,
  ISwitchLocale
> = (options?) => {
  const { mutate } = UseRequestProcessor();

  const switchLocaleFn = async (payload: ISwitchLocale): Promise<any> => {
    const response = await api.put<any>(
      `${getURL("LOCALE")}/switch/`,
      payload
    );

    return response.data;
  };

  const mutation: UseMutationResult<any, any, ISwitchLocale> =
    mutate(
      ["useSwitchLocale"],
      async (payload: ISwitchLocale) => {
        const res = await switchLocaleFn(payload);
        return res;
      },
      options,
    );

  return mutation;
};
