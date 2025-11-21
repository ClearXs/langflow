import { UseQueryResult, useQuery } from "@tanstack/react-query";
import { GlobalVariable } from "@/types/global_variables";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";

export const useGetSystemVariables = (): UseQueryResult<
  GlobalVariable[],
  Error
> => {
  const getSystemVariablesFn = async () => {
    const res = await api.get<GlobalVariable[]>(
      `${getURL("VARIABLES")}/system`,
    );
    return res.data;
  };

  const queryResult = useQuery({
    queryKey: ["system-variables"],
    queryFn: getSystemVariablesFn,
    refetchOnWindowFocus: false,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
    gcTime: 10 * 60 * 1000, // Garbage collect after 10 minutes
  });

  return queryResult;
};
