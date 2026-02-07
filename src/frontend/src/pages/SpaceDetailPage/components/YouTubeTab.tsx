import { Loader2, Youtube } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface YouTubeTabProps {
  spaceId: number;
  onSuccess?: () => void;
}

export function YouTubeTab({ spaceId, onSuccess }: YouTubeTabProps) {
  const { t } = useTranslation();
  const [url, setUrl] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);

  const extractVideoId = (url: string): string | null => {
    // Support multiple YouTube URL formats
    const patterns = [
      /(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)/,
      /youtube\.com\/embed\/([^&\n?#]+)/,
      /youtube\.com\/v\/([^&\n?#]+)/,
    ];

    for (const pattern of patterns) {
      const match = url.match(pattern);
      if (match && match[1]) {
        return match[1];
      }
    }
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!url.trim()) {
      toast.error(t("spaces.documents.youtube.url_required"));
      return;
    }

    const videoId = extractVideoId(url);
    if (!videoId) {
      toast.error(t("spaces.documents.youtube.invalid_url"));
      return;
    }

    setIsProcessing(true);

    try {
      // TODO: Implement API call to add YouTube video
      // const response = await api.post('/api/v1/documents/youtube', {
      //   video_id: videoId,
      //   url: url,
      //   search_space_id: spaceId,
      // });

      // Simulate API call for now
      await new Promise((resolve) => setTimeout(resolve, 2000));

      toast.success(t("spaces.documents.youtube.success"));
      setUrl("");
      onSuccess?.();
    } catch (error) {
      toast.error(
        t("spaces.documents.youtube.error", {
          error: error instanceof Error ? error.message : "Unknown error",
        }),
      );
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Icon and Description */}
      <div className="flex flex-col items-center text-center space-y-3">
        <div className="rounded-full bg-red-100 dark:bg-red-900/20 p-4">
          <Youtube className="h-8 w-8 text-red-600 dark:text-red-400" />
        </div>
        <div className="space-y-1">
          <h3 className="text-lg font-semibold">
            {t("spaces.documents.youtube.title")}
          </h3>
          <p className="text-sm text-muted-foreground max-w-md">
            {t("spaces.documents.youtube.description")}
          </p>
        </div>
      </div>

      {/* URL Input Form */}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="youtube-url">
            {t("spaces.documents.youtube.url_label")}
          </Label>
          <Input
            id="youtube-url"
            type="url"
            placeholder="https://www.youtube.com/watch?v=..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={isProcessing}
            className="w-full"
          />
          <p className="text-xs text-muted-foreground">
            {t("spaces.documents.youtube.url_hint")}
          </p>
        </div>

        {/* Example URLs */}
        <div className="rounded-lg border bg-muted/50 p-3 space-y-2">
          <p className="text-xs font-medium text-muted-foreground">
            {t("spaces.documents.youtube.supported_formats")}:
          </p>
          <ul className="text-xs text-muted-foreground space-y-1">
            <li>• https://www.youtube.com/watch?v=VIDEO_ID</li>
            <li>• https://youtu.be/VIDEO_ID</li>
            <li>• https://www.youtube.com/embed/VIDEO_ID</li>
          </ul>
        </div>

        {/* Submit Button */}
        <div className="flex justify-end">
          <Button type="submit" disabled={isProcessing || !url.trim()}>
            {isProcessing ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {t("spaces.documents.youtube.processing")}
              </>
            ) : (
              <>
                <Youtube className="mr-2 h-4 w-4" />
                {t("spaces.documents.youtube.add_video")}
              </>
            )}
          </Button>
        </div>
      </form>

      {/* Feature List */}
      <div className="rounded-lg border p-4 space-y-3">
        <p className="text-sm font-medium">
          {t("spaces.documents.youtube.features_title")}
        </p>
        <ul className="text-sm text-muted-foreground space-y-2">
          <li className="flex items-start gap-2">
            <span className="text-primary mt-0.5">✓</span>
            <span>{t("spaces.documents.youtube.feature_transcript")}</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-primary mt-0.5">✓</span>
            <span>{t("spaces.documents.youtube.feature_metadata")}</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-primary mt-0.5">✓</span>
            <span>{t("spaces.documents.youtube.feature_search")}</span>
          </li>
        </ul>
      </div>
    </div>
  );
}
