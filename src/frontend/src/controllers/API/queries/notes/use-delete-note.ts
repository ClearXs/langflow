import type { DeleteNoteResponse, useMutationFunctionType } from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IDeleteNote {
  searchSpaceId: number;
  noteId: number;
}

export const useDeleteNote: useMutationFunctionType<
  DeleteNoteResponse,
  IDeleteNote
> = (options?) => {
  const { mutate, queryClient } = UseRequestProcessor();

  const deleteNoteFn = async (
    payload: IDeleteNote,
  ): Promise<DeleteNoteResponse> => {
    const res = await api.delete(
      `/api/v1/notes/search-spaces/${payload.searchSpaceId}/notes/${payload.noteId}`,
    );
    return res.data;
  };

  const mutation = mutate(["useDeleteNote"], deleteNoteFn, {
    onSettled: () => {
      queryClient.refetchQueries({ queryKey: ["useGetNotes"] });
      queryClient.refetchQueries({ queryKey: ["useGetDocuments"] });
    },
    ...options,
  });

  return mutation;
};
