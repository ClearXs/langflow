import { formatDistanceToNow } from "date-fns";
import {
  Calendar,
  FileText,
  MoreVertical,
  Plus,
  Search,
  Trash2,
} from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import {
  useDeleteNote,
  useGetNotesQuery,
  usePostCreateNote,
} from "@/controllers/API/queries/notes";

export default function NotesPage() {
  const { t } = useTranslation();
  const { spaceId } = useParams<{ spaceId: string }>();
  const [searchQuery, setSearchQuery] = useState("");
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [newNoteTitle, setNewNoteTitle] = useState("");

  const {
    data: notes = [],
    isLoading,
    refetch,
  } = useGetNotesQuery(
    { search_space_id: Number(spaceId) },
    { enabled: !!spaceId },
  );

  const { mutateAsync: createNote, isPending: isCreating } =
    usePostCreateNote();
  const { mutateAsync: deleteNote, isPending: isDeleting } = useDeleteNote();

  const filteredNotes = notes.filter((note) =>
    note.title.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  const handleCreateNote = async () => {
    if (!newNoteTitle.trim()) {
      toast.error(t("spaces.notes.enterTitle"));
      return;
    }

    try {
      await createNote({
        title: newNoteTitle,
        content: "",
        search_space_id: Number(spaceId),
      });
      toast.success(t("spaces.notes.createSuccess"));
      setNewNoteTitle("");
      setIsCreateDialogOpen(false);
      refetch();
    } catch (error) {
      toast.error(t("spaces.notes.createError"));
    }
  };

  const handleDeleteNote = async (noteId: number) => {
    try {
      await deleteNote({ id: noteId });
      toast.success(t("spaces.notes.deleteSuccess"));
      refetch();
    } catch (error) {
      toast.error(t("spaces.notes.deleteError"));
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Notes Header */}
      <div className="border-b px-6 py-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold">{t("spaces.notes.title")}</h2>
            <p className="text-sm text-muted-foreground">
              {t("spaces.notes.subtitle")}
            </p>
          </div>
          <Button onClick={() => setIsCreateDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            {t("spaces.notes.createNote")}
          </Button>
        </div>

        {/* Search */}
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder={t("spaces.notes.searchPlaceholder")}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
      </div>

      {/* Notes Content */}
      <div className="flex-1 overflow-auto p-6">
        {isLoading && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <Card key={i} className="animate-pulse">
                <CardHeader>
                  <div className="h-5 bg-muted rounded w-3/4" />
                </CardHeader>
                <CardContent>
                  <div className="h-16 bg-muted rounded" />
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {!isLoading && filteredNotes.length === 0 && (
          <div className="h-full flex items-center justify-center">
            <Card className="max-w-md border-dashed">
              <CardContent className="flex flex-col items-center justify-center py-16">
                <div className="rounded-full bg-muted p-4 mb-4">
                  <FileText className="h-8 w-8 text-muted-foreground" />
                </div>
                <h3 className="text-lg font-semibold mb-2">
                  {searchQuery
                    ? t("spaces.notes.noNotesFound")
                    : t("spaces.notes.noNotesYet")}
                </h3>
                <p className="text-muted-foreground text-center max-w-sm mb-6">
                  {searchQuery
                    ? t("spaces.notes.tryAdjusting")
                    : t("spaces.notes.createFirstNote")}
                </p>
                {!searchQuery && (
                  <Button onClick={() => setIsCreateDialogOpen(true)}>
                    <Plus className="mr-2 h-4 w-4" />
                    {t("spaces.notes.createYourFirstNote")}
                  </Button>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {!isLoading && filteredNotes.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredNotes.map((note) => (
              <Card key={note.id} className="hover:shadow-md transition-shadow">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold line-clamp-1">
                        {note.title}
                      </h3>
                    </div>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 w-8 p-0"
                        >
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem
                          onClick={() => handleDeleteNote(note.id)}
                          className="text-destructive"
                        >
                          <Trash2 className="mr-2 h-4 w-4" />
                          {t("spaces.notes.delete")}
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </CardHeader>

                <CardContent>
                  <div className="text-sm text-muted-foreground line-clamp-3">
                    {note.content || t("spaces.notes.emptyNote")}
                  </div>
                </CardContent>

                <CardFooter className="text-xs text-muted-foreground flex items-center gap-2">
                  <Calendar className="h-3 w-3" />
                  {t("spaces.notes.updated")}{" "}
                  {formatDistanceToNow(new Date(note.updated_at), {
                    addSuffix: true,
                  })}
                </CardFooter>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Create Note Dialog */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("spaces.notes.createDialogTitle")}</DialogTitle>
            <DialogDescription>
              {t("spaces.notes.createDialogDescription")}
            </DialogDescription>
          </DialogHeader>

          <div className="py-4">
            <Input
              placeholder={t("spaces.notes.noteTitlePlaceholder")}
              value={newNoteTitle}
              onChange={(e) => setNewNoteTitle(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !isCreating) {
                  handleCreateNote();
                }
              }}
              autoFocus
            />
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setIsCreateDialogOpen(false)}
              disabled={isCreating}
            >
              {t("common.cancel")}
            </Button>
            <Button onClick={handleCreateNote} disabled={isCreating}>
              {isCreating
                ? t("spaces.notes.creating")
                : t("spaces.notes.createNote")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
