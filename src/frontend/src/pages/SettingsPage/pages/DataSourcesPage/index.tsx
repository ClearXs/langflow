import {
  AlertCircle,
  CheckCircle,
  Database,
  Edit,
  Loader2,
  Plus,
  RefreshCw,
  TestTube,
  Trash2,
  XCircle,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  createDataSource,
  deleteDataSource,
  getDataSources,
  testConnection,
  testDataSourceConnection,
  updateDataSource,
} from "@/controllers/API/datasources";
import DeleteConfirmationModal from "@/modals/deleteConfirmationModal";
import useAlertStore from "@/stores/alertStore";
import { convertUTCToLocalTimezone } from "@/utils/utils";

interface DataSource {
  id: string;
  name: string;
  type: string;
  host?: string;
  port?: number;
  database?: string;
  username?: string;
  status?: "active" | "inactive" | "error";
  lastTested?: string;
  metadata?: {
    created_at: string;
    updated_at?: string;
  };
}

interface DataSourceFormData {
  name: string;
  type: string;
  host: string;
  port: string;
  database: string;
  username: string;
  password: string;
}

interface FormErrors {
  name?: string;
  host?: string;
  port?: string;
  database?: string;
  username?: string;
  password?: string;
}

export default function DataSourcesPage() {
  const { t } = useTranslation();
  const setSuccessData = useAlertStore((state) => state.setSuccessData);
  const setErrorData = useAlertStore((state) => state.setErrorData);

  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [loading, setLoading] = useState(false);
  const [testingConnection, setTestingConnection] = useState<string | null>(
    null,
  );
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingDataSource, setEditingDataSource] = useState<DataSource | null>(
    null,
  );
  const [searchTerm, setSearchTerm] = useState("");
  const [formErrors, setFormErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [dataSourceToDelete, setDataSourceToDelete] =
    useState<DataSource | null>(null);

  const [formData, setFormData] = useState<DataSourceFormData>({
    name: "",
    type: "mysql",
    host: "",
    port: "3306",
    database: "",
    username: "",
    password: "",
  });

  // Database type options with default ports
  // Only support MySQL, PostgreSQL, Hive, and Neo4j
  const databaseTypes = [
    { value: "mysql", label: "MySQL", defaultPort: "3306" },
    { value: "postgresql", label: "PostgreSQL", defaultPort: "5432" },
    { value: "hive", label: "Hive", defaultPort: "10000" },
    { value: "neo4j", label: "Neo4j", defaultPort: "7687" },
  ];

  useEffect(() => {
    loadDataSources();
  }, []);

  const loadDataSources = async () => {
    setLoading(true);
    try {
      const dataSources = await getDataSources();
      setDataSources(dataSources);
    } catch (error: any) {
      console.error("Failed to load data sources:", error);
      setErrorData({
        title: t("dataSource.errors.loadFailed"),
        list: [error?.message || String(error)],
      });
    } finally {
      setLoading(false);
    }
  };

  const handleTestConnection = async (dataSource: DataSource) => {
    setTestingConnection(dataSource.id);
    try {
      // Use the new API endpoint that fetches the password from storage
      const result = await testDataSourceConnection(dataSource.id);

      if (result.status === "success") {
        setSuccessData({
          title: t("dataSource.connectionSuccess"),
        });
        // Update status in list
        setDataSources((prev) =>
          prev.map((ds) =>
            ds.id === dataSource.id
              ? {
                  ...ds,
                  status: "active",
                  lastTested: new Date().toISOString(),
                }
              : ds,
          ),
        );
      } else {
        setErrorData({
          title: t("dataSource.connectionFailed", { error: result.message }),
        });
      }
    } catch (error: any) {
      setErrorData({
        title: t("dataSource.connectionFailed", {
          error: error?.message || String(error),
        }),
      });
    } finally {
      setTestingConnection(null);
    }
  };

  const validateForm = (): boolean => {
    const errors: FormErrors = {};

    // Required field validation
    if (!formData.name.trim()) {
      errors.name = t("dataSource.errors.nameRequired");
    }

    if (!formData.host.trim()) {
      errors.host = t("dataSource.errors.hostRequired");
    }

    if (!formData.port.trim()) {
      errors.port = t("dataSource.errors.portRequired");
    } else if (
      isNaN(parseInt(formData.port)) ||
      parseInt(formData.port) < 1 ||
      parseInt(formData.port) > 65535
    ) {
      errors.port = t("dataSource.errors.portInvalid");
    }

    if (!formData.database.trim()) {
      errors.database = t("dataSource.errors.databaseRequired");
    }

    // Username and password are optional for Hive only
    const isHive = formData.type.toLowerCase() === "hive";
    if (!isHive) {
      if (!formData.username.trim()) {
        errors.username = t("dataSource.errors.usernameRequired");
      }

      // Password is required only for new data sources
      if (!editingDataSource && !formData.password.trim()) {
        errors.password = t("dataSource.errors.passwordRequired");
      }
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleCreateOrUpdate = async () => {
    // Validate form before submission
    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);
    try {
      const dataSourceData = {
        ...formData,
        port: parseInt(formData.port),
      };

      if (editingDataSource) {
        await updateDataSource(editingDataSource.id, dataSourceData);
        setSuccessData({
          title: t("dataSource.updateSuccess"),
        });
      } else {
        await createDataSource(dataSourceData);
        setSuccessData({
          title: t("dataSource.createSuccess"),
        });
      }

      setDialogOpen(false);
      resetForm();
      loadDataSources();
    } catch (error: any) {
      setErrorData({
        title: editingDataSource
          ? t("dataSource.errors.updateFailed")
          : t("dataSource.errors.createFailed"),
        list: [error?.message || String(error)],
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteDataSource(id);
      setSuccessData({
        title: t("dataSource.deleteSuccess"),
      });
      setDeleteDialogOpen(false);
      setDataSourceToDelete(null);
      loadDataSources();
    } catch (error: any) {
      setErrorData({
        title: t("dataSource.errors.deleteFailed"),
        list: [error?.message || String(error)],
      });
    }
  };

  const openDeleteDialog = (dataSource: DataSource) => {
    setDataSourceToDelete(dataSource);
    setDeleteDialogOpen(true);
  };

  const handleEdit = (dataSource: DataSource) => {
    setEditingDataSource(dataSource);
    setFormData({
      name: dataSource.name,
      type: dataSource.type,
      host: dataSource.host || "",
      port: dataSource.port?.toString() || "3306",
      database: dataSource.database || "",
      username: dataSource.username || "",
      password: "", // Don't show existing password
    });
    setFormErrors({}); // Clear any previous errors
    setDialogOpen(true);
  };

  const resetForm = () => {
    setFormData({
      name: "",
      type: "mysql",
      host: "",
      port: "3306",
      database: "",
      username: "",
      password: "",
    });
    setEditingDataSource(null);
    setFormErrors({});
  };

  const handleTypeChange = (type: string) => {
    const dbType = databaseTypes.find((db) => db.value === type);
    setFormData({
      ...formData,
      type,
      port: dbType?.defaultPort || "3306",
    });
  };

  // Filter data sources based on search
  const filteredDataSources = dataSources.filter((ds) => {
    if (searchTerm && !ds.name.toLowerCase().includes(searchTerm.toLowerCase()))
      return false;
    return true;
  });

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <Database className="h-6 w-6" />
          <h1 className="text-2xl font-bold">{t("dataSource.management")}</h1>
        </div>
        <p className="text-muted-foreground">{t("dataSource.description")}</p>
      </div>

      {/* Toolbar */}
      <div className="flex items-center justify-between gap-4">
        <Input
          placeholder={t("dataSource.searchPlaceholder")}
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="max-w-sm"
        />
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={loadDataSources}
            disabled={loading}
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            {t("common.refresh")}
          </Button>
          <Button
            onClick={() => {
              resetForm();
              setDialogOpen(true);
            }}
          >
            <Plus className="h-4 w-4 mr-2" />
            {t("dataSource.addDataSource")}
          </Button>
        </div>
      </div>

      {/* Data Sources Table */}
      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t("dataSource.name")}</TableHead>
              <TableHead>{t("dataSource.type")}</TableHead>
              <TableHead>{t("dataSource.host")}</TableHead>
              <TableHead>{t("dataSource.database")}</TableHead>
              <TableHead>{t("dataSource.status")}</TableHead>
              <TableHead>{t("dataSource.lastTested")}</TableHead>
              <TableHead className="text-right">
                {t("dataSource.actions")}
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8">
                  <Loader2 className="h-8 w-8 animate-spin mx-auto mb-2" />
                  <p>{t("common.loading")}</p>
                </TableCell>
              </TableRow>
            ) : filteredDataSources.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8">
                  <Database className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                  <p className="text-muted-foreground">
                    {t("dataSource.noDataSources")}
                  </p>
                </TableCell>
              </TableRow>
            ) : (
              filteredDataSources.map((dataSource) => (
                <TableRow key={dataSource.id}>
                  <TableCell className="font-medium">
                    {dataSource.name}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">
                      {dataSource.type.toUpperCase()}
                    </Badge>
                  </TableCell>
                  <TableCell>{dataSource.host || "-"}</TableCell>
                  <TableCell>{dataSource.database || "-"}</TableCell>
                  <TableCell>
                    {dataSource.status === "active" ? (
                      <Badge variant="default" className="bg-green-600">
                        <CheckCircle className="h-3 w-3 mr-1" />
                        {t("dataSource.statusActive")}
                      </Badge>
                    ) : dataSource.status === "error" ? (
                      <Badge variant="destructive">
                        <XCircle className="h-3 w-3 mr-1" />
                        {t("dataSource.statusError")}
                      </Badge>
                    ) : (
                      <Badge variant="secondary">
                        {t("dataSource.statusInactive")}
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    {dataSource.lastTested
                      ? convertUTCToLocalTimezone(dataSource.lastTested)
                      : "-"}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleTestConnection(dataSource)}
                        disabled={testingConnection === dataSource.id}
                      >
                        {testingConnection === dataSource.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <TestTube className="h-4 w-4" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleEdit(dataSource)}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <DeleteConfirmationModal
                        open={
                          deleteDialogOpen &&
                          dataSourceToDelete?.id === dataSource.id
                        }
                        setOpen={(open) => {
                          if (!open) {
                            setDeleteDialogOpen(false);
                            setDataSourceToDelete(null);
                          }
                        }}
                        onConfirm={() => handleDelete(dataSource.id)}
                        description={
                          t("dataSource.dataSource") + " " + dataSource.name
                        }
                      >
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => openDeleteDialog(dataSource)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </DeleteConfirmationModal>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingDataSource
                ? t("dataSource.editDataSource")
                : t("dataSource.addDataSource")}
            </DialogTitle>
            <DialogDescription>
              {editingDataSource
                ? t("dataSource.editDescription")
                : t("dataSource.addDescription")}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">
                {t("dataSource.name")} <span className="text-red-500">*</span>
              </Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => {
                  setFormData({ ...formData, name: e.target.value });
                  if (formErrors.name) {
                    setFormErrors({ ...formErrors, name: undefined });
                  }
                }}
                placeholder={t("dataSource.namePlaceholder")}
                className={formErrors.name ? "border-red-500" : ""}
              />
              {formErrors.name && (
                <p className="text-sm text-red-500 flex items-center gap-1">
                  <AlertCircle className="h-3 w-3" />
                  {formErrors.name}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="type">
                {t("dataSource.type")} <span className="text-red-500">*</span>
              </Label>
              <Select value={formData.type} onValueChange={handleTypeChange}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {databaseTypes.map((db) => (
                    <SelectItem key={db.value} value={db.value}>
                      {db.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="host">
                  {t("dataSource.host")} <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="host"
                  value={formData.host}
                  onChange={(e) => {
                    setFormData({ ...formData, host: e.target.value });
                    if (formErrors.host) {
                      setFormErrors({ ...formErrors, host: undefined });
                    }
                  }}
                  placeholder="localhost"
                  className={formErrors.host ? "border-red-500" : ""}
                />
                {formErrors.host && (
                  <p className="text-sm text-red-500 flex items-center gap-1">
                    <AlertCircle className="h-3 w-3" />
                    {formErrors.host}
                  </p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="port">
                  {t("dataSource.port")} <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="port"
                  value={formData.port}
                  onChange={(e) => {
                    setFormData({ ...formData, port: e.target.value });
                    if (formErrors.port) {
                      setFormErrors({ ...formErrors, port: undefined });
                    }
                  }}
                  placeholder="3306"
                  className={formErrors.port ? "border-red-500" : ""}
                />
                {formErrors.port && (
                  <p className="text-sm text-red-500 flex items-center gap-1">
                    <AlertCircle className="h-3 w-3" />
                    {formErrors.port}
                  </p>
                )}
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="database">
                {t("dataSource.database")}{" "}
                <span className="text-red-500">*</span>
              </Label>
              <Input
                id="database"
                value={formData.database}
                onChange={(e) => {
                  setFormData({ ...formData, database: e.target.value });
                  if (formErrors.database) {
                    setFormErrors({ ...formErrors, database: undefined });
                  }
                }}
                placeholder={t("dataSource.databasePlaceholder")}
                className={formErrors.database ? "border-red-500" : ""}
              />
              {formErrors.database && (
                <p className="text-sm text-red-500 flex items-center gap-1">
                  <AlertCircle className="h-3 w-3" />
                  {formErrors.database}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="username">
                {t("dataSource.username")}{" "}
                {formData.type.toLowerCase() !== "hive" && (
                  <span className="text-red-500">*</span>
                )}
              </Label>
              <Input
                id="username"
                value={formData.username}
                onChange={(e) => {
                  setFormData({ ...formData, username: e.target.value });
                  if (formErrors.username) {
                    setFormErrors({ ...formErrors, username: undefined });
                  }
                }}
                placeholder={t("dataSource.usernamePlaceholder")}
                className={formErrors.username ? "border-red-500" : ""}
              />
              {formErrors.username && (
                <p className="text-sm text-red-500 flex items-center gap-1">
                  <AlertCircle className="h-3 w-3" />
                  {formErrors.username}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">
                {t("dataSource.password")}
                {!editingDataSource &&
                  formData.type.toLowerCase() !== "hive" && (
                    <span className="text-red-500">*</span>
                  )}
              </Label>
              <Input
                id="password"
                type="password"
                value={formData.password}
                onChange={(e) => {
                  setFormData({ ...formData, password: e.target.value });
                  if (formErrors.password) {
                    setFormErrors({ ...formErrors, password: undefined });
                  }
                }}
                placeholder={
                  editingDataSource
                    ? t("dataSource.passwordUnchanged")
                    : t("dataSource.passwordPlaceholder")
                }
                className={formErrors.password ? "border-red-500" : ""}
              />
              {formErrors.password && (
                <p className="text-sm text-red-500 flex items-center gap-1">
                  <AlertCircle className="h-3 w-3" />
                  {formErrors.password}
                </p>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDialogOpen(false)}
              disabled={isSubmitting}
            >
              {t("common.cancel")}
            </Button>
            <Button onClick={handleCreateOrUpdate} disabled={isSubmitting}>
              {isSubmitting ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : null}
              {editingDataSource ? t("common.update") : t("common.create")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
