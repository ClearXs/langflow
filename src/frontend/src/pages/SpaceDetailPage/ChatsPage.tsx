import { AssistantRuntimeProvider } from "@assistant-ui/react";
import { MessageSquare, Plus } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";
import { Thread } from "@/components/assistant-ui/thread";
import { ChatHeader } from "@/components/new-chat/chat-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import useChatStore from "@/stores/chatStore";
import useSpacesStore from "@/stores/spacesStore";

export default function ChatsPage() {
  const { t } = useTranslation();
  const { spaceId } = useParams<{ spaceId: string }>();
  const [threadId, setThreadId] = useState<string | null>(null);
  const { currentChatId, setCurrentChatId } = useChatStore();
  const activeSpace = useSpacesStore((state) => state.getActiveSpace());

  // For now, show a functional chat interface placeholder
  // In the future, this will integrate with the backend chat API
  const hasActiveChat = threadId !== null;

  const handleNewChat = () => {
    // Create a new chat thread
    const newThreadId = `thread-${Date.now()}`;
    setThreadId(newThreadId);
    setCurrentChatId(newThreadId);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Chat Header */}
      <div className="border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold">
              {activeSpace?.name || t("spaces.chats.title")}
            </h2>
            <p className="text-sm text-muted-foreground">
              {t("spaces.chats.subtitle")}
            </p>
          </div>
          <Button onClick={handleNewChat}>
            <Plus className="mr-2 h-4 w-4" />
            {t("spaces.chats.newChat")}
          </Button>
        </div>
      </div>

      {/* Chat Content */}
      <div className="flex-1 overflow-auto">
        {!hasActiveChat ? (
          <div className="h-full flex items-center justify-center p-8">
            <Card className="max-w-md border-dashed">
              <CardContent className="flex flex-col items-center justify-center py-16">
                <div className="rounded-full bg-muted p-4 mb-4">
                  <MessageSquare className="h-8 w-8 text-muted-foreground" />
                </div>
                <h3 className="text-lg font-semibold mb-2">
                  {t("spaces.chats.startConversation")}
                </h3>
                <p className="text-muted-foreground text-center max-w-sm mb-6">
                  {t("spaces.chats.startConversationDesc")}
                </p>
                <Button onClick={handleNewChat}>
                  <Plus className="mr-2 h-4 w-4" />
                  {t("spaces.chats.newChat")}
                </Button>
              </CardContent>
            </Card>
          </div>
        ) : (
          <div className="h-full">
            {/* Chat Interface Placeholder */}
            <div className="max-w-4xl mx-auto p-6">
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-sm font-medium">
                    {t("spaces.chats.you")}
                  </div>
                  <div className="flex-1 bg-muted rounded-lg p-4">
                    <p className="text-sm">
                      {t("spaces.chats.placeholderMessage")}
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-secondary text-secondary-foreground flex items-center justify-center text-sm font-medium">
                    {t("spaces.chats.ai")}
                  </div>
                  <div className="flex-1 bg-muted/50 rounded-lg p-4">
                    <p className="text-sm text-muted-foreground">
                      {t("spaces.chats.featuresTitle")}
                    </p>
                    <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
                      <li>• {t("spaces.chats.streaming")}</li>
                      <li>• {t("spaces.chats.mentions")}</li>
                      <li>• {t("spaces.chats.multiTurn")}</li>
                      <li>• {t("spaces.chats.connectors")}</li>
                      <li>• {t("spaces.chats.persistence")}</li>
                    </ul>
                  </div>
                </div>
              </div>

              {/* Input Area Placeholder */}
              <div className="mt-6 border-t pt-4">
                <div className="flex items-center gap-2 p-4 border rounded-lg bg-background">
                  <input
                    type="text"
                    placeholder={t("spaces.chats.placeholderDisabled")}
                    className="flex-1 bg-transparent outline-none text-sm"
                    disabled
                  />
                  <Button size="sm" disabled>
                    {t("spaces.chats.send")}
                  </Button>
                </div>
                <p className="mt-2 text-xs text-center text-muted-foreground">
                  Space ID: {spaceId} | Thread ID: {threadId}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
