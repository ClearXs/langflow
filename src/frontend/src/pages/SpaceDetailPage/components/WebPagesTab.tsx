import { Globe, Loader2, Plus, X } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";

interface WebPagesTabProps {
  spaceId: number;
  onSuccess?: () => void;
}

export function WebPagesTab({ spaceId, onSuccess }: WebPagesTabProps) {
  const { t } = useTranslation();
  const [urls, setUrls] = useState<string[]>([""]);
  const [crawlSubpages, setCrawlSubpages] = useState(false);
  const [maxDepth, setMaxDepth] = useState(1);
  const [isProcessing, setIsProcessing] = useState(false);

  const isValidUrl = (url: string): boolean => {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  };

  const addUrlField = () => {
    setUrls([...urls, ""]);
  };

  const removeUrlField = (index: number) => {
    setUrls(urls.filter((_, i) => i !== index));
  };

  const updateUrl = (index: number, value: string) => {
    const newUrls = [...urls];
    newUrls[index] = value;
    setUrls(newUrls);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const validUrls = urls.filter((url) => url.trim() && isValidUrl(url));

    if (validUrls.length === 0) {
      toast.error(t("spaces.documents.web.no_valid_urls"));
      return;
    }

    setIsProcessing(true);

    try {
      // TODO: Implement API call to crawl web pages
      // const response = await api.post('/api/v1/documents/web-crawl', {
      //   urls: validUrls,
      //   search_space_id: spaceId,
      //   crawl_subpages: crawlSubpages,
      //   max_depth: maxDepth,
      // });

      // Simulate API call for now
      await new Promise((resolve) => setTimeout(resolve, 2000));

      toast.success(
        t("spaces.documents.web.success", { count: validUrls.length }),
      );
      setUrls([""]);
      setCrawlSubpages(false);
      onSuccess?.();
    } catch (error) {
      toast.error(
        t("spaces.documents.web.error", {
          error: error instanceof Error ? error.message : "Unknown error",
        }),
      );
    } finally {
      setIsProcessing(false);
    }
  };

  const validUrlCount = urls.filter(
    (url) => url.trim() && isValidUrl(url),
  ).length;

  return (
    <div className="space-y-6">
      {/* Icon and Description */}
      <div className="flex flex-col items-center text-center space-y-3">
        <div className="rounded-full bg-blue-100 dark:bg-blue-900/20 p-4">
          <Globe className="h-8 w-8 text-blue-600 dark:text-blue-400" />
        </div>
        <div className="space-y-1">
          <h3 className="text-lg font-semibold">
            {t("spaces.documents.web.title")}
          </h3>
          <p className="text-sm text-muted-foreground max-w-md">
            {t("spaces.documents.web.description")}
          </p>
        </div>
      </div>

      {/* URL Input Form */}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <Label>{t("spaces.documents.web.urls_label")}</Label>
            {validUrlCount > 0 && (
              <Badge variant="secondary" className="text-xs">
                {validUrlCount} {t("spaces.documents.web.valid_urls")}
              </Badge>
            )}
          </div>

          {/* URL Fields */}
          <div className="space-y-2">
            {urls.map((url, index) => (
              <div key={index} className="flex gap-2">
                <Input
                  type="url"
                  placeholder="https://example.com/docs"
                  value={url}
                  onChange={(e) => updateUrl(index, e.target.value)}
                  disabled={isProcessing}
                  className="flex-1"
                />
                {urls.length > 1 && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => removeUrlField(index)}
                    disabled={isProcessing}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                )}
              </div>
            ))}
          </div>

          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={addUrlField}
            disabled={isProcessing}
            className="w-full"
          >
            <Plus className="mr-2 h-4 w-4" />
            {t("spaces.documents.web.add_url")}
          </Button>
        </div>

        {/* Crawl Options */}
        <div className="rounded-lg border p-4 space-y-4">
          <p className="text-sm font-medium">
            {t("spaces.documents.web.crawl_options")}
          </p>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="crawl-subpages" className="text-sm">
                {t("spaces.documents.web.crawl_subpages")}
              </Label>
              <p className="text-xs text-muted-foreground">
                {t("spaces.documents.web.crawl_subpages_hint")}
              </p>
            </div>
            <Switch
              id="crawl-subpages"
              checked={crawlSubpages}
              onCheckedChange={setCrawlSubpages}
              disabled={isProcessing}
            />
          </div>

          {crawlSubpages && (
            <div className="space-y-2">
              <Label htmlFor="max-depth" className="text-sm">
                {t("spaces.documents.web.max_depth")}: {maxDepth}
              </Label>
              <input
                id="max-depth"
                type="range"
                min="1"
                max="5"
                value={maxDepth}
                onChange={(e) => setMaxDepth(Number(e.target.value))}
                disabled={isProcessing}
                className="w-full"
              />
              <p className="text-xs text-muted-foreground">
                {t("spaces.documents.web.max_depth_hint")}
              </p>
            </div>
          )}
        </div>

        {/* Submit Button */}
        <div className="flex justify-end">
          <Button type="submit" disabled={isProcessing || validUrlCount === 0}>
            {isProcessing ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {t("spaces.documents.web.crawling")}
              </>
            ) : (
              <>
                <Globe className="mr-2 h-4 w-4" />
                {t("spaces.documents.web.start_crawl")}
              </>
            )}
          </Button>
        </div>
      </form>

      {/* Feature List */}
      <div className="rounded-lg border p-4 space-y-3">
        <p className="text-sm font-medium">
          {t("spaces.documents.web.features_title")}
        </p>
        <ul className="text-sm text-muted-foreground space-y-2">
          <li className="flex items-start gap-2">
            <span className="text-primary mt-0.5">✓</span>
            <span>{t("spaces.documents.web.feature_clean_text")}</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-primary mt-0.5">✓</span>
            <span>{t("spaces.documents.web.feature_structure")}</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-primary mt-0.5">✓</span>
            <span>{t("spaces.documents.web.feature_links")}</span>
          </li>
        </ul>
      </div>
    </div>
  );
}
