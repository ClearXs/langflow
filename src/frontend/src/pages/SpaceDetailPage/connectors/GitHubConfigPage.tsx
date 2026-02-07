import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, Check, Globe, Loader2 } from "lucide-react";
import { motion } from "motion/react";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import * as z from "zod";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  useGetConnectorsQuery,
  usePostCreateConnector,
} from "@/controllers/API/queries/connectors";

// Form schema for GitHub PAT
const githubPatFormSchema = z.object({
  name: z.string().min(3, {
    message: "Connector name must be at least 3 characters.",
  }),
  github_pat: z
    .string()
    .min(20, {
      message: "GitHub Personal Access Token seems too short.",
    })
    .refine((pat) => pat.startsWith("ghp_") || pat.startsWith("github_pat_"), {
      message: "GitHub PAT should start with 'ghp_' or 'github_pat_'",
    }),
});

type GithubPatFormValues = z.infer<typeof githubPatFormSchema>;

// Type for GitHub repositories
interface GithubRepo {
  id: number;
  name: string;
  full_name: string;
  private: boolean;
  url: string;
  description: string | null;
  last_updated: string | null;
}

export default function GitHubConfigPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { spaceId } = useParams<{ spaceId: string }>();
  const [step, setStep] = useState<"enter_pat" | "select_repos">("enter_pat");
  const [isFetchingRepos, setIsFetchingRepos] = useState(false);
  const [isCreatingConnector, setIsCreatingConnector] = useState(false);
  const [repositories, setRepositories] = useState<GithubRepo[]>([]);
  const [selectedRepos, setSelectedRepos] = useState<string[]>([]);
  const [connectorName, setConnectorName] = useState<string>("GitHub");
  const [validatedPat, setValidatedPat] = useState<string>("");
  const [doesConnectorExist, setDoesConnectorExist] = useState(false);

  const { data: connectors = [] } = useGetConnectorsQuery(
    { enabled: !!spaceId },
    { search_space_id: Number(spaceId) },
  );

  const { mutateAsync: createConnector } = usePostCreateConnector();

  // Initialize the form
  const form = useForm<GithubPatFormValues>({
    resolver: zodResolver(githubPatFormSchema),
    defaultValues: {
      name: connectorName,
      github_pat: "",
    },
  });

  // Check if GitHub connector already exists
  useEffect(() => {
    const exists = connectors.some(
      (c) => c.connector_type === "github-connector",
    );
    setDoesConnectorExist(exists);
  }, [connectors]);

  // Fetch repositories (mock for now - needs backend endpoint)
  const fetchRepositories = async (values: GithubPatFormValues) => {
    setIsFetchingRepos(true);
    setConnectorName(values.name);
    setValidatedPat(values.github_pat);

    try {
      // TODO: Call backend API to fetch repositories
      // For now, mock data
      const mockRepos: GithubRepo[] = [
        {
          id: 1,
          name: "my-repo",
          full_name: "username/my-repo",
          private: false,
          url: "https://github.com/username/my-repo",
          description: "My awesome repository",
          last_updated: new Date().toISOString(),
        },
      ];

      setRepositories(mockRepos);
      setStep("select_repos");
      toast.success(
        t("connectors.github.repos_found", { count: mockRepos.length }),
      );
    } catch (error) {
      console.error("Error fetching GitHub repositories:", error);
      toast.error(
        error instanceof Error
          ? error.message
          : t("connectors.github.fetch_failed"),
      );
    } finally {
      setIsFetchingRepos(false);
    }
  };

  // Handle connector creation
  const handleCreateConnector = async () => {
    if (selectedRepos.length === 0) {
      toast.warning(t("connectors.github.select_repos_warning"));
      return;
    }

    setIsCreatingConnector(true);
    try {
      await createConnector({
        data: {
          name: connectorName,
          connector_type: "github-connector",
          search_space_id: Number(spaceId),
          config: {
            GITHUB_PAT: validatedPat,
            repo_full_names: selectedRepos,
          },
        },
      });

      toast.success(t("connectors.github.create_success"));
      navigate(`/spaces/${spaceId}/connectors`);
    } catch (error) {
      console.error("Error creating GitHub connector:", error);
      toast.error(
        error instanceof Error
          ? error.message
          : t("connectors.github.create_failed"),
      );
    } finally {
      setIsCreatingConnector(false);
    }
  };

  // Handle repo selection
  const handleRepoSelection = (repoFullName: string, checked: boolean) => {
    setSelectedRepos((prev) =>
      checked
        ? [...prev, repoFullName]
        : prev.filter((name) => name !== repoFullName),
    );
  };

  const handleGoBack = () => {
    if (step === "select_repos") {
      setStep("enter_pat");
      setRepositories([]);
      setSelectedRepos([]);
      setValidatedPat("");
      form.reset({ name: connectorName, github_pat: "" });
    } else {
      navigate(`/spaces/${spaceId}/sources/add?tab=connectors`);
    }
  };

  if (doesConnectorExist) {
    return (
      <div className="container mx-auto py-8 max-w-2xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <Button
            variant="ghost"
            onClick={() =>
              navigate(`/spaces/${spaceId}/sources/add?tab=connectors`)
            }
            className="mb-6"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            {t("common.back")}
          </Button>

          <Card>
            <CardHeader>
              <CardTitle>✅ {t("connectors.github.success_title")}</CardTitle>
              <CardDescription>
                {t("connectors.github.success_description")}
              </CardDescription>
            </CardHeader>
            <CardFooter>
              <Button onClick={() => navigate(`/spaces/${spaceId}/connectors`)}>
                {t("connectors.manage.view_manage")}
              </Button>
            </CardFooter>
          </Card>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 max-w-3xl">
      <Button variant="ghost" className="mb-6" onClick={handleGoBack}>
        <ArrowLeft className="mr-2 h-4 w-4" />
        {step === "select_repos"
          ? t("connectors.github.back_to_pat")
          : t("common.back")}
      </Button>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        {/* Header */}
        <div className="mb-8 flex items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-muted">
            <Globe className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">
              {t("connectors.github.title")}
            </h1>
            <p className="text-muted-foreground">
              {t("connectors.github.subtitle")}
            </p>
          </div>
        </div>

        {/* Step 1: Enter PAT */}
        {step === "enter_pat" && (
          <Card>
            <CardHeader>
              <CardTitle>{t("connectors.github.setup_title")}</CardTitle>
              <CardDescription>
                {t("connectors.github.setup_description")}
              </CardDescription>
            </CardHeader>
            <Form {...form}>
              <form onSubmit={form.handleSubmit(fetchRepositories)}>
                <CardContent className="space-y-4">
                  <FormField
                    control={form.control}
                    name="name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          {t("connectors.github.name_label")}
                        </FormLabel>
                        <FormControl>
                          <Input
                            placeholder={t(
                              "connectors.github.name_placeholder",
                            )}
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          {t("connectors.github.name_description")}
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="github_pat"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          {t("connectors.github.pat_label")}
                        </FormLabel>
                        <FormControl>
                          <Input
                            type="password"
                            placeholder="ghp_xxxxxxxxxxxxx"
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          {t("connectors.github.pat_description")}
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <Alert>
                    <AlertTitle>
                      {t("connectors.github.how_to_get_pat")}
                    </AlertTitle>
                    <AlertDescription>
                      <ol className="list-decimal list-inside space-y-1 text-sm mt-2">
                        <li>{t("connectors.github.pat_step_1")}</li>
                        <li>{t("connectors.github.pat_step_2")}</li>
                        <li>{t("connectors.github.pat_step_3")}</li>
                      </ol>
                    </AlertDescription>
                  </Alert>
                </CardContent>
                <CardFooter className="flex justify-between">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() =>
                      navigate(`/spaces/${spaceId}/sources/add?tab=connectors`)
                    }
                  >
                    {t("common.cancel")}
                  </Button>
                  <Button type="submit" disabled={isFetchingRepos}>
                    {isFetchingRepos ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        {t("connectors.github.fetching_repos")}
                      </>
                    ) : (
                      t("connectors.github.next_step")
                    )}
                  </Button>
                </CardFooter>
              </form>
            </Form>
          </Card>
        )}

        {/* Step 2: Select Repositories */}
        {step === "select_repos" && (
          <Card>
            <CardHeader>
              <CardTitle>{t("connectors.github.select_repos_title")}</CardTitle>
              <CardDescription>
                {t("connectors.github.select_repos_description", {
                  count: repositories.length,
                })}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {repositories.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-8">
                    {t("connectors.github.no_repos")}
                  </p>
                ) : (
                  <div className="space-y-2 max-h-96 overflow-y-auto">
                    {repositories.map((repo) => (
                      <div
                        key={repo.id}
                        className="flex items-start space-x-3 p-3 border rounded-lg hover:bg-muted/50"
                      >
                        <Checkbox
                          id={`repo-${repo.id}`}
                          checked={selectedRepos.includes(repo.full_name)}
                          onCheckedChange={(checked) =>
                            handleRepoSelection(
                              repo.full_name,
                              checked as boolean,
                            )
                          }
                        />
                        <div className="flex-1">
                          <label
                            htmlFor={`repo-${repo.id}`}
                            className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                          >
                            {repo.full_name}
                          </label>
                          {repo.description && (
                            <p className="text-sm text-muted-foreground mt-1">
                              {repo.description}
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </CardContent>
            <CardFooter className="flex justify-between">
              <Button type="button" variant="outline" onClick={handleGoBack}>
                {t("common.back")}
              </Button>
              <Button
                onClick={handleCreateConnector}
                disabled={isCreatingConnector || selectedRepos.length === 0}
              >
                {isCreatingConnector ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {t("connectors.github.creating")}
                  </>
                ) : (
                  <>
                    <Check className="mr-2 h-4 w-4" />
                    {t("connectors.github.create_button", {
                      count: selectedRepos.length,
                    })}
                  </>
                )}
              </Button>
            </CardFooter>
          </Card>
        )}
      </motion.div>
    </div>
  );
}
