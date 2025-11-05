import {
  AlertCircle,
  CheckCircle,
  Loader2,
  TestTube,
  XCircle,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
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
  createDataSource,
  testConnection,
} from "@/controllers/API/datasources";
import useAlertStore from "@/stores/alertStore";
import useDatasourceDialogStore from "@/stores/datasourceDialogStore";

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

export default function DataSourceDialog() {
  const { t } = useTranslation();
  const setSuccessData = useAlertStore((state) => state.setSuccessData);
  const setErrorData = useAlertStore((state) => state.setErrorData);
  const isOpen = useDatasourceDialogStore((state) => state.isOpen);
  const closeDialog = useDatasourceDialogStore((state) => state.closeDialog);

  const [formErrors, setFormErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [testStatus, setTestStatus] = useState<"idle" | "success" | "error">(
    "idle",
  );

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
    setFormErrors({});
    setTestStatus("idle");
  };

  const handleTypeChange = (type: string) => {
    const selectedType = databaseTypes.find((t) => t.value === type);
    setFormData({
      ...formData,
      type,
      port: selectedType?.defaultPort || formData.port,
    });
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

    // Validate database (not required for Neo4j)
    const isNeo4j = formData.type.toLowerCase() === "neo4j";
    if (!isNeo4j && !formData.database.trim()) {
      errors.database = t("dataSource.errors.databaseRequired");
    }

    // Username and password are optional for Hive only
    const isHive = formData.type.toLowerCase() === "hive";
    if (!isHive) {
      if (!formData.username.trim()) {
        errors.username = t("dataSource.errors.usernameRequired");
      }

      if (!formData.password.trim()) {
        errors.password = t("dataSource.errors.passwordRequired");
      }
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleTestConnection = async () => {
    // Validate required fields for connection test
    const requiredErrors: FormErrors = {};
    if (!formData.host.trim()) {
      requiredErrors.host = t("dataSource.errors.hostRequired");
    }
    if (!formData.port.trim()) {
      requiredErrors.port = t("dataSource.errors.portRequired");
    } else if (
      isNaN(parseInt(formData.port)) ||
      parseInt(formData.port) < 1 ||
      parseInt(formData.port) > 65535
    ) {
      requiredErrors.port = t("dataSource.errors.portInvalid");
    }
    // Database is optional for Neo4j
    const isNeo4j = formData.type.toLowerCase() === "neo4j";
    if (!isNeo4j && !formData.database.trim()) {
      requiredErrors.database = t("dataSource.errors.databaseRequired");
    }

    // Username and password are optional for Hive only
    const isHive = formData.type.toLowerCase() === "hive";
    if (!isHive) {
      if (!formData.username.trim()) {
        requiredErrors.username = t("dataSource.errors.usernameRequired");
      }
      if (!formData.password.trim()) {
        requiredErrors.password = t("dataSource.errors.passwordRequired");
      }
    }

    if (Object.keys(requiredErrors).length > 0) {
      setFormErrors(requiredErrors);
      return;
    }

    setIsTesting(true);
    setTestStatus("idle");
    try {
      const result = await testConnection({
        host: formData.host,
        port: parseInt(formData.port),
        database: formData.database,
        username: formData.username,
        password: formData.password,
        type: formData.type,
      });

      if (result.status === "success") {
        setTestStatus("success");
        setSuccessData({
          title: t("dataSource.connectionSuccess"),
        });
      } else {
        setTestStatus("error");
        setErrorData({
          title: t("dataSource.connectionFailed", { error: result.message }),
        });
      }
    } catch (error: any) {
      setTestStatus("error");
      setErrorData({
        title: t("dataSource.connectionFailed", {
          error: error?.message || String(error),
        }),
      });
    } finally {
      setIsTesting(false);
    }
  };

  const handleCreate = async () => {
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

      await createDataSource(dataSourceData);
      setSuccessData({
        title: t("dataSource.createSuccess"),
      });

      closeDialog();
      resetForm();

      // Trigger a custom event to notify that a datasource was created
      window.dispatchEvent(new CustomEvent("datasource-created"));
    } catch (error: any) {
      setErrorData({
        title: t("dataSource.errors.createFailed"),
        list: [error?.message || String(error)],
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    closeDialog();
    resetForm();
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("dataSource.addDataSource")}</DialogTitle>
          <DialogDescription>
            {t("dataSource.addDescription")}
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
                {databaseTypes.map((type) => (
                  <SelectItem key={type.value} value={type.value}>
                    {type.label}
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
                placeholder={t("dataSource.hostPlaceholder")}
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
                placeholder={t("dataSource.portPlaceholder")}
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
              {formData.type.toLowerCase() !== "neo4j" && (
                <span className="text-red-500">*</span>
              )}
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
              {t("dataSource.password")}{" "}
              {formData.type.toLowerCase() !== "hive" && (
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
              placeholder={t("dataSource.passwordPlaceholder")}
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
        <DialogFooter className="flex justify-between items-center">
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              onClick={handleTestConnection}
              disabled={isSubmitting || isTesting}
            >
              {isTesting ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <TestTube className="h-4 w-4 mr-2" />
              )}
              {t("dataSource.testConnection")}
            </Button>
            {testStatus === "success" && (
              <div className="flex items-center gap-1 text-green-600">
                <CheckCircle className="h-4 w-4" />
                <span className="text-sm">
                  {t("dataSource.connectionSuccess")}
                </span>
              </div>
            )}
            {testStatus === "error" && (
              <div className="flex items-center gap-1 text-red-600">
                <XCircle className="h-4 w-4" />
                <span className="text-sm">
                  {t("dataSource.connectionFailed", { error: "" })}
                </span>
              </div>
            )}
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={handleClose}
              disabled={isSubmitting}
            >
              {t("common.cancel")}
            </Button>
            <Button onClick={handleCreate} disabled={isSubmitting}>
              {isSubmitting ? t("common.loading") : t("common.create")}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
