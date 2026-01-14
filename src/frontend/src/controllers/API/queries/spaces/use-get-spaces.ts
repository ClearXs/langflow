import type { SpaceWithStats, useQueryFunctionType } from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

export const useGetSpacesQuery: useQueryFunctionType<
  undefined,
  SpaceWithStats[]
> = (options) => {
  const { query } = UseRequestProcessor();

  const getSpacesFn = async (): Promise<SpaceWithStats[]> => {
    const res = await api.get(`${getURL("SPACES")}/`);
    return res.data;
  };

  const queryResult = query(["useGetSpaces"], getSpacesFn, options);
  return queryResult;
};
