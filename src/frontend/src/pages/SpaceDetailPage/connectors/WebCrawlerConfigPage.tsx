import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, Check, Globe, Loader2 } from "lucide-react";
import { motion } from "motion/react";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import * as z from "zod";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  useGetConnectorsQuery,
  usePostCreateConnector,
} from "@/controllers/API/queries/connectors";

// Define the form schema
const webcrawlerFormSchema = z.object({
  name: z.string().min(3, {
    message: "Connector name must be at least 3 characters.",
  }),
  api_key: z.string().optional(),
  initial_urls: z.string().optional(),
});

type WebcrawlerFormValues = z.infer<typeof webcrawlerFormSchema>;

export default function WebCrawlerConfigPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { spaceId } = useParams<{ spaceId: string }>();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [doesConnectorExist, setDoesConnectorExist] = useState(false);

  const { data: connectors = [] } = useGetConnectorsQuery(
    { enabled: !!spaceId },
    { search_space_id: Number(spaceId) },
  );

  const { mutateAsync: createConnector } = usePostCreateConnector();

  // Initialize the form
  const form = useForm<WebcrawlerFormValues>({
    resolver: zodResolver(webcrawlerFormSchema),
    defaultValues: {
      name: "Web Pages",
      api_key: "",
      initial_urls: "",
    },
  });

  // Check if webcrawler connector already exists
  useEffect(() => {
    const exists = connectors.some(
      (c) => c.connector_type === "webcrawler-connector",
    );
    setDoesConnectorExist(exists);
  }, [connectors]);

  // Handle form submission
  const onSubmit = async (values: WebcrawlerFormValues) => {
    setIsSubmitting(true);
    try {
      const config: Record<string, string> = {};

      if (values.api_key && values.api_key.trim()) {
        config.FIRECRAWL_API_KEY = values.api_key;
      }

      if (values.initial_urls && values.initial_urls.trim()) {
        config.INITIAL_URLS = values.initial_urls;
      }

      await createConnector({
        data: {
          name: values.name,
          connector_type: "webcrawler-connector",
          search_space_id: Number(spaceId),
          config: config,
        },
      });

      toast.success(t("connectors.webcrawler.create_success"));
      navigate(`/spaces/${spaceId}/connectors`);
    } catch (error) {
      console.error("Error creating connector:", error);
      toast.error(
        error instanceof Error
          ? error.message
          : t("connectors.webcrawler.create_failed"),
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleGoBack = () => {
    navigate(`/spaces/${spaceId}/sources/add?tab=connectors`);
  };

  return (
    <div className="container mx-auto py-8 max-w-2xl">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        {/* Header */}
        <div className="mb-8">
          <Button
            variant="ghost"
            onClick={handleGoBack}
            className="mb-4 inline-flex items-center text-sm"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            {t("common.back")}
          </Button>
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-muted">
              <Globe className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight">
                {t("connectors.webcrawler.title")}
              </h1>
              <p className="text-muted-foreground">
                {t("connectors.webcrawler.subtitle")}
              </p>
            </div>
          </div>
        </div>

        {/* Connection Card */}
        {!doesConnectorExist ? (
          <Card>
            <CardHeader>
              <CardTitle>{t("connectors.webcrawler.setup_title")}</CardTitle>
              <CardDescription>
                {t("connectors.webcrawler.setup_description")}
              </CardDescription>
            </CardHeader>
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)}>
                <CardContent className="space-y-4">
                  <FormField
                    control={form.control}
                    name="name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          {t("connectors.webcrawler.name_label")}
                        </FormLabel>
                        <FormControl>
                          <Input
                            placeholder={t(
                              "connectors.webcrawler.name_placeholder",
                            )}
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          {t("connectors.webcrawler.name_description")}
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="api_key"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          {t("connectors.webcrawler.api_key_label")}
                        </FormLabel>
                        <FormControl>
                          <Input
                            type="password"
                            placeholder="fc-xxxxxxxxxxxxx"
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          {t("connectors.webcrawler.api_key_description")}
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="initial_urls"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          {t("connectors.webcrawler.urls_label")}
                        </FormLabel>
                        <FormControl>
                          <Textarea
                            placeholder="https://example.com&#10;https://docs.example.com"
                            className="min-h-[100px] font-mono text-sm"
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          {t("connectors.webcrawler.urls_description")}
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <div className="space-y-2 pt-2">
                    <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                      <Check className="h-4 w-4 text-green-500" />
                      <span>{t("connectors.webcrawler.feature_1")}</span>
                    </div>
                    <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                      <Check className="h-4 w-4 text-green-500" />
                      <span>{t("connectors.webcrawler.feature_2")}</span>
                    </div>
                    <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                      <Check className="h-4 w-4 text-green-500" />
                      <span>{t("connectors.webcrawler.feature_3")}</span>
                    </div>
                    <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                      <Check className="h-4 w-4 text-green-500" />
                      <span>{t("connectors.webcrawler.feature_4")}</span>
                    </div>
                  </div>
                </CardContent>
                <CardFooter className="flex justify-between">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleGoBack}
                  >
                    {t("common.cancel")}
                  </Button>
                  <Button type="submit" disabled={isSubmitting}>
                    {isSubmitting ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        {t("connectors.webcrawler.creating")}
                      </>
                    ) : (
                      <>
                        <Globe className="mr-2 h-4 w-4" />
                        {t("connectors.webcrawler.create_button")}
                      </>
                    )}
                  </Button>
                </CardFooter>
              </form>
            </Form>
          </Card>
        ) : (
          /* Success Card */
          <Card>
            <CardHeader>
              <CardTitle>
                ✅ {t("connectors.webcrawler.success_title")}
              </CardTitle>
              <CardDescription>
                {t("connectors.webcrawler.success_description")}
              </CardDescription>
            </CardHeader>
            <CardFooter>
              <Button onClick={() => navigate(`/spaces/${spaceId}/connectors`)}>
                {t("connectors.manage.view_manage")}
              </Button>
            </CardFooter>
          </Card>
        )}

        {/* Help Section */}
        {!doesConnectorExist && (
          <Card className="mt-6">
            <CardHeader>
              <CardTitle className="text-lg">
                {t("connectors.webcrawler.how_it_works")}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h4 className="font-medium mb-2">
                  {t("connectors.webcrawler.step_1_title")}
                </h4>
                <p className="text-sm text-muted-foreground">
                  {t("connectors.webcrawler.step_1_firecrawl")}
                </p>
                <p className="text-sm text-muted-foreground mt-2">
                  {t("connectors.webcrawler.step_1_fallback")}
                </p>
              </div>
              <div>
                <h4 className="font-medium mb-2">
                  {t("connectors.webcrawler.step_2_title")}
                </h4>
                <p className="text-sm text-muted-foreground">
                  {t("connectors.webcrawler.step_2_description")}
                </p>
              </div>
              <div>
                <h4 className="font-medium mb-2">
                  {t("connectors.webcrawler.step_3_title")}
                </h4>
                <p className="text-sm text-muted-foreground">
                  {t("connectors.webcrawler.step_3_description")}
                </p>
              </div>
            </CardContent>
          </Card>
        )}
      </motion.div>
    </div>
  );
}
