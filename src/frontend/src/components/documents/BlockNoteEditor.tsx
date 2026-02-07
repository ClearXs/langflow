import { useEffect, useMemo } from "react";
import { useCreateBlockNote } from "@blocknote/react";
import { BlockNoteView } from "@blocknote/mantine";
import "@blocknote/mantine/style.css";
import { useDarkStore } from "@/stores/darkStore";

interface BlockNoteEditorProps {
  initialContent: any[];
  onChange: (content: any[]) => void;
  editable?: boolean;
}

export default function BlockNoteEditor({
  initialContent,
  onChange,
  editable = true,
}: BlockNoteEditorProps) {
  const dark = useDarkStore((state) => state.dark);

  // Normalize blocks to ensure they have required fields and proper StyledText format
  const normalizedContent = useMemo(() => {
    if (!initialContent || initialContent.length === 0) {
      return undefined;
    }

    return initialContent.map((block) => {
      // Normalize content array to ensure each text item has styles property
      const normalizedContentArray = (block.content || []).map((item: any) => {
        if (item.type === "text") {
          return {
            type: "text",
            text: item.text || "",
            styles: item.styles || {},
          };
        }
        return item;
      });

      return {
        id: block.id || crypto.randomUUID(),
        type: block.type || "paragraph",
        props: block.props || {},
        content: normalizedContentArray,
        children: block.children || [],
      };
    });
  }, [initialContent]);

  const editor = useCreateBlockNote({
    initialContent: normalizedContent,
  });

  useEffect(() => {
    if (!editable) {
      editor.isEditable = false;
    }
  }, [editable, editor]);

  const handleChange = () => {
    onChange(editor.document);
  };

  return (
    <div className="blocknote-editor">
      <BlockNoteView
        editor={editor}
        theme={dark ? "dark" : "light"}
        onChange={handleChange}
      />
    </div>
  );
}
