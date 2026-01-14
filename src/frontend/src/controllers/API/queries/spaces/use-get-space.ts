import type { SpaceRead, useQueryFunctionType } from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IGetSpace {
  spaceId: number;
}

export const useGetSpaceQuery: useQueryFunctionType<IGetSpace, SpaceRead> = (
  options,
  { spaceId },
) => {
  const { query } = UseRequestProcessor();

  const getSpaceFn = async (): Promise<SpaceRead> => {
    const res = await api.get(`${getURL("SPACES")}/${spaceId}`);
    return res.data;
  };

  const queryResult = query(["useGetSpace", spaceId], getSpaceFn, {
    enabled: !!spaceId,
    ...options,
  });
  return queryResult;
};
