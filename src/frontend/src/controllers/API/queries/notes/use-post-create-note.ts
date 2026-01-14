import type {
  CreateNoteRequest,
  NoteRead,
  useMutationFunctionType,
} from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IPostCreateNote {
  searchSpaceId: number;
  data: CreateNoteRequest;
}

export const usePostCreateNote: useMutationFunctionType<
  NoteRead,
  IPostCreateNote
> = (options?) => {
  const { mutate, queryClient } = UseRequestProcessor();

  const createNoteFn = async (payload: IPostCreateNote): Promise<NoteRead> => {
    const res = await api.post(
      `/api/v1/notes/search-spaces/${payload.searchSpaceId}/notes`,
      payload.data,
    );
    return res.data;
  };

  const mutation = mutate(["usePostCreateNote"], createNoteFn, {
    onSettled: () => {
      queryClient.refetchQueries({ queryKey: ["useGetNotes"] });
      queryClient.refetchQueries({ queryKey: ["useGetDocuments"] });
    },
    ...options,
  });

  return mutation;
};
