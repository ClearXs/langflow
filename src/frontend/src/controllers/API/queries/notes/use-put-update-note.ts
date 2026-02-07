import { useMutationFunctionType } from "@/types/api";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface UpdateNoteRequest {
  searchSpaceId: number;
  noteId: number;
  data: {
    title?: string;
    content?: string;
  };
}

export const usePutUpdateNote: useMutationFunctionType<
  undefined,
  UpdateNoteRequest
> = (options?) => {
  const { mutate, queryClient } = UseRequestProcessor();

  const updateNoteFn = async ({
    searchSpaceId,
    noteId,
    data,
  }: UpdateNoteRequest): Promise<any> => {
    const response = await api.put(
      `/api/v1/notes/search-spaces/${searchSpaceId}/notes/${noteId}`,
      data,
    );

    return response?.data;
  };

  const mutation = mutate(["usePutUpdateNote"], updateNoteFn, {
    onSettled: () => {
      queryClient.refetchQueries({ queryKey: ["useGetNotes"] });
    },
    ...options,
  });

  return mutation;
};
