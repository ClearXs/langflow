import type {
  NoteRead,
  PaginatedResponse,
  useQueryFunctionType,
} from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IGetNotes {
  searchSpaceId: number;
  skip?: number;
  page?: number;
  page_size?: number;
}

export const useGetNotesQuery: useQueryFunctionType<
  IGetNotes,
  PaginatedResponse<NoteRead>
> = (options, { searchSpaceId, skip, page, page_size = 50 }) => {
  const { query } = UseRequestProcessor();

  const getNotesFn = async (): Promise<PaginatedResponse<NoteRead>> => {
    const params = new URLSearchParams();
    if (skip !== undefined) params.append("skip", skip.toString());
    if (page !== undefined) params.append("page", page.toString());
    if (page_size !== undefined)
      params.append("page_size", page_size.toString());

    const res = await api.get(
      `/api/v1/notes/search-spaces/${searchSpaceId}/notes?${params.toString()}`,
    );
    return res.data;
  };

  const queryResult = query(
    ["useGetNotes", searchSpaceId, skip, page, page_size],
    getNotesFn,
    {
      enabled: !!searchSpaceId,
      ...options,
    },
  );
  return queryResult;
};
