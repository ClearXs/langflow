import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, Check, Loader2, LucideIcon } from "lucide-react";
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
import {
  useGetConnectorsQuery,
  usePostCreateConnector,
} from "@/controllers/API/queries/connectors";

interface ApiKeyConnectorConfig {
  connectorType: string;
  icon: React.ReactNode;
  translationKey: string;
  apiKeyLabel: string;
  apiKeyPlaceholder: string;
  apiKeyField: string; // The config field name for the API key
  additionalFields?: {
    name: string;
    label: string;
    placeholder: string;
    configKey: string;
    required?: boolean;
  }[];
  features?: string[];
}

// Define form schema factory
const createFormSchema = (hasAdditionalFields: boolean) => {
  const baseSchema = {
    name: z.string().min(3, {
      message: "Connector name must be at least 3 characters.",
    }),
    api_key: z.string().min(1, {
      message: "API key is required.",
    }),
  };

  return z.object(baseSchema);
};

export default function ApiKeyConnectorPage({
  config,
}: {
  config: ApiKeyConnectorConfig;
}) {
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

  const formSchema = createFormSchema(!!config.additionalFields);

  // Initialize the form
  const form = useForm({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: t(`connectors.${config.translationKey}.default_name`),
      api_key: "",
    },
  });

  // Check if connector already exists
  useEffect(() => {
    const exists = connectors.some(
      (c) => c.connector_type === config.connectorType,
    );
    setDoesConnectorExist(exists);
  }, [connectors, config.connectorType]);

  // Handle form submission
  const onSubmit = async (values: any) => {
    setIsSubmitting(true);
    try {
      const configData: Record<string, string> = {
        [config.apiKeyField]: values.api_key,
      };

      // Add additional fields if present
      if (config.additionalFields) {
        config.additionalFields.forEach((field) => {
          if (values[field.name]) {
            configData[field.configKey] = values[field.name];
          }
        });
      }

      await createConnector({
        data: {
          name: values.name,
          connector_type: config.connectorType,
          search_space_id: Number(spaceId),
          config: configData,
        },
      });

      toast.success(t(`connectors.${config.translationKey}.create_success`));
      navigate(`/spaces/${spaceId}/connectors`);
    } catch (error) {
      console.error("Error creating connector:", error);
      toast.error(
        error instanceof Error
          ? error.message
          : t(`connectors.${config.translationKey}.create_failed`),
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
              {config.icon}
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight">
                {t(`connectors.${config.translationKey}.title`)}
              </h1>
              <p className="text-muted-foreground">
                {t(`connectors.${config.translationKey}.subtitle`)}
              </p>
            </div>
          </div>
        </div>

        {/* Connection Card */}
        {!doesConnectorExist ? (
          <Card>
            <CardHeader>
              <CardTitle>
                {t(`connectors.${config.translationKey}.setup_title`)}
              </CardTitle>
              <CardDescription>
                {t(`connectors.${config.translationKey}.setup_description`)}
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
                          {t(`connectors.${config.translationKey}.name_label`)}
                        </FormLabel>
                        <FormControl>
                          <Input
                            placeholder={t(
                              `connectors.${config.translationKey}.name_placeholder`,
                            )}
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          {t(
                            `connectors.${config.translationKey}.name_description`,
                          )}
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
                        <FormLabel>{config.apiKeyLabel}</FormLabel>
                        <FormControl>
                          <Input
                            type="password"
                            placeholder={config.apiKeyPlaceholder}
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          {t(
                            `connectors.${config.translationKey}.api_key_description`,
                          )}
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {/* Additional fields */}
                  {config.additionalFields?.map((additionalField) => (
                    <FormField
                      key={additionalField.name}
                      control={form.control}
                      name={additionalField.name}
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>
                            {additionalField.label}
                            {!additionalField.required && " (Optional)"}
                          </FormLabel>
                          <FormControl>
                            <Input
                              placeholder={additionalField.placeholder}
                              {...field}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  ))}

                  {/* Features list */}
                  {config.features && (
                    <div className="space-y-2 pt-2">
                      {config.features.map((feature, index) => (
                        <div
                          key={index}
                          className="flex items-center space-x-2 text-sm text-muted-foreground"
                        >
                          <Check className="h-4 w-4 text-green-500" />
                          <span>
                            {t(
                              `connectors.${config.translationKey}.feature_${index + 1}`,
                            )}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
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
                        {t(`connectors.${config.translationKey}.creating`)}
                      </>
                    ) : (
                      <>
                        {config.icon}
                        <span className="ml-2">
                          {t(
                            `connectors.${config.translationKey}.create_button`,
                          )}
                        </span>
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
                ✅ {t(`connectors.${config.translationKey}.success_title`)}
              </CardTitle>
              <CardDescription>
                {t(`connectors.${config.translationKey}.success_description`)}
              </CardDescription>
            </CardHeader>
            <CardFooter>
              <Button onClick={() => navigate(`/spaces/${spaceId}/connectors`)}>
                {t("connectors.manage.view_manage")}
              </Button>
            </CardFooter>
          </Card>
        )}
      </motion.div>
    </div>
  );
}
