import {
  AlertCircle,
  CheckCircle,
  Loader2,
  TestTube,
  XCircle,
} from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
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
  advanced_config: Record<string, any>;
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
    advanced_config: {},
  });

  // Database type options with default ports
  // Support MySQL, PostgreSQL, Hive, Neo4j, Kafka, and Flink
  const databaseTypes = [
    { value: "mysql", label: "MySQL", defaultPort: "3306" },
    { value: "postgresql", label: "PostgreSQL", defaultPort: "5432" },
    { value: "hive", label: "Hive", defaultPort: "10000" },
    { value: "neo4j", label: "Neo4j", defaultPort: "7687" },
    { value: "kafka", label: "Kafka", defaultPort: "9092" },
    { value: "flink", label: "Flink", defaultPort: "8081" },
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
      advanced_config: {},
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
      advanced_config: {}, // Reset advanced config when type changes
    });
  };

  const handleAdvancedConfigChange = (key: string, value: any) => {
    setFormData({
      ...formData,
      advanced_config: {
        ...formData.advanced_config,
        [key]: value,
      },
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

    // Validate database (not required for Neo4j, Kafka, Flink)
    const isNeo4j = formData.type.toLowerCase() === "neo4j";
    const isKafka = formData.type.toLowerCase() === "kafka";
    const isFlink = formData.type.toLowerCase() === "flink";
    if (!isNeo4j && !isKafka && !isFlink && !formData.database.trim()) {
      errors.database = t("dataSource.errors.databaseRequired");
    }

    // Username and password are optional for Hive, Kafka, and Flink
    const isHive = formData.type.toLowerCase() === "hive";
    if (!isHive && !isKafka && !isFlink) {
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
    // Database is optional for Neo4j, Kafka, Flink
    const isNeo4j = formData.type.toLowerCase() === "neo4j";
    const isKafka = formData.type.toLowerCase() === "kafka";
    const isFlink = formData.type.toLowerCase() === "flink";
    if (!isNeo4j && !isKafka && !isFlink && !formData.database.trim()) {
      requiredErrors.database = t("dataSource.errors.databaseRequired");
    }

    // Username and password are optional for Hive, Kafka, and Flink
    const isHive = formData.type.toLowerCase() === "hive";
    if (!isHive && !isKafka && !isFlink) {
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
        name: formData.name,
        type: formData.type as import("@/controllers/API/datasources").DataSourceType,
        host: formData.host,
        port: parseInt(formData.port),
        database: formData.database,
        username: formData.username,
        password: formData.password,
        advanced_config: formData.advanced_config,
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
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
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
          {/* Host field - full width for Kafka/Flink, half width for others */}
          {formData.type.toLowerCase() === "kafka" ||
          formData.type.toLowerCase() === "flink" ? (
            <div className="space-y-2">
              <Label htmlFor="host">
                {formData.type.toLowerCase() === "kafka"
                  ? t("dataSource.kafkaBootstrapServers")
                  : t("dataSource.flinkRestAddress")}{" "}
                <span className="text-red-500">*</span>
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
                placeholder={
                  formData.type.toLowerCase() === "kafka"
                    ? t("dataSource.kafkaBootstrapServersPlaceholder")
                    : t("dataSource.flinkRestAddressPlaceholder")
                }
                className={formErrors.host ? "border-red-500" : ""}
              />
              {formErrors.host && (
                <p className="text-sm text-red-500 flex items-center gap-1">
                  <AlertCircle className="h-3 w-3" />
                  {formErrors.host}
                </p>
              )}
            </div>
          ) : (
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
          )}
          {formData.type.toLowerCase() !== "kafka" &&
            formData.type.toLowerCase() !== "flink" && (
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
            )}
          {formData.type.toLowerCase() !== "kafka" &&
            formData.type.toLowerCase() !== "flink" && (
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
            )}
          {formData.type.toLowerCase() !== "kafka" &&
            formData.type.toLowerCase() !== "flink" && (
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
            )}

          {/* Advanced Configuration Accordion */}
          <Accordion type="single" collapsible className="w-full">
            <AccordionItem value="advanced-config">
              <AccordionTrigger>
                {t("dataSource.advancedConfig")}
              </AccordionTrigger>
              <AccordionContent>
                <div className="space-y-4 pt-2">
                  {/* MySQL Advanced Config */}
                  {formData.type === "mysql" && (
                    <>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label htmlFor="connect_timeout">
                            {t("dataSource.advanced.connect_timeout")}
                          </Label>
                          <Input
                            id="connect_timeout"
                            type="number"
                            value={
                              formData.advanced_config.connect_timeout || ""
                            }
                            onChange={(e) =>
                              handleAdvancedConfigChange(
                                "connect_timeout",
                                e.target.value
                                  ? parseInt(e.target.value)
                                  : undefined,
                              )
                            }
                            placeholder={t(
                              "dataSource.advanced.connect_timeout_placeholder",
                            )}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="read_timeout">
                            {t("dataSource.advanced.read_timeout")}
                          </Label>
                          <Input
                            id="read_timeout"
                            type="number"
                            value={formData.advanced_config.read_timeout || ""}
                            onChange={(e) =>
                              handleAdvancedConfigChange(
                                "read_timeout",
                                e.target.value
                                  ? parseInt(e.target.value)
                                  : undefined,
                              )
                            }
                            placeholder={t(
                              "dataSource.advanced.read_timeout_placeholder",
                            )}
                          />
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label htmlFor="write_timeout">
                            {t("dataSource.advanced.write_timeout")}
                          </Label>
                          <Input
                            id="write_timeout"
                            type="number"
                            value={formData.advanced_config.write_timeout || ""}
                            onChange={(e) =>
                              handleAdvancedConfigChange(
                                "write_timeout",
                                e.target.value
                                  ? parseInt(e.target.value)
                                  : undefined,
                              )
                            }
                            placeholder={t(
                              "dataSource.advanced.write_timeout_placeholder",
                            )}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="charset">
                            {t("dataSource.advanced.charset")}
                          </Label>
                          <Select
                            value={formData.advanced_config.charset || ""}
                            onValueChange={(value) =>
                              handleAdvancedConfigChange("charset", value)
                            }
                          >
                            <SelectTrigger>
                              <SelectValue
                                placeholder={t(
                                  "dataSource.advanced.select_charset",
                                )}
                              />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="utf8">utf8</SelectItem>
                              <SelectItem value="utf8mb4">utf8mb4</SelectItem>
                              <SelectItem value="latin1">latin1</SelectItem>
                              <SelectItem value="ascii">ascii</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="ssl_ca">
                          {t("dataSource.advanced.ssl_ca")}
                        </Label>
                        <Input
                          id="ssl_ca"
                          value={formData.advanced_config.ssl_ca || ""}
                          onChange={(e) =>
                            handleAdvancedConfigChange("ssl_ca", e.target.value)
                          }
                          placeholder={t(
                            "dataSource.advanced.ssl_ca_placeholder",
                          )}
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label htmlFor="ssl_cert">
                            {t("dataSource.advanced.ssl_cert")}
                          </Label>
                          <Input
                            id="ssl_cert"
                            value={formData.advanced_config.ssl_cert || ""}
                            onChange={(e) =>
                              handleAdvancedConfigChange(
                                "ssl_cert",
                                e.target.value,
                              )
                            }
                            placeholder={t(
                              "dataSource.advanced.ssl_cert_placeholder",
                            )}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="ssl_key">
                            {t("dataSource.advanced.ssl_key")}
                          </Label>
                          <Input
                            id="ssl_key"
                            value={formData.advanced_config.ssl_key || ""}
                            onChange={(e) =>
                              handleAdvancedConfigChange(
                                "ssl_key",
                                e.target.value,
                              )
                            }
                            placeholder={t(
                              "dataSource.advanced.ssl_key_placeholder",
                            )}
                          />
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <input
                          id="ssl_disabled"
                          type="checkbox"
                          checked={
                            formData.advanced_config.ssl_disabled || false
                          }
                          onChange={(e) =>
                            handleAdvancedConfigChange(
                              "ssl_disabled",
                              e.target.checked,
                            )
                          }
                          className="h-4 w-4"
                        />
                        <Label htmlFor="ssl_disabled">
                          {t("dataSource.advanced.ssl_disabled")}
                        </Label>
                      </div>
                    </>
                  )}

                  {/* PostgreSQL Advanced Config */}
                  {formData.type === "postgresql" && (
                    <>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label htmlFor="connect_timeout">
                            {t("dataSource.advanced.connect_timeout")}
                          </Label>
                          <Input
                            id="connect_timeout"
                            type="number"
                            value={
                              formData.advanced_config.connect_timeout || ""
                            }
                            onChange={(e) =>
                              handleAdvancedConfigChange(
                                "connect_timeout",
                                e.target.value
                                  ? parseInt(e.target.value)
                                  : undefined,
                              )
                            }
                            placeholder={t(
                              "dataSource.advanced.connect_timeout_placeholder",
                            )}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="statement_timeout">
                            {t("dataSource.advanced.statement_timeout")}
                          </Label>
                          <Input
                            id="statement_timeout"
                            type="number"
                            value={
                              formData.advanced_config.statement_timeout || ""
                            }
                            onChange={(e) =>
                              handleAdvancedConfigChange(
                                "statement_timeout",
                                e.target.value
                                  ? parseInt(e.target.value)
                                  : undefined,
                              )
                            }
                            placeholder={t(
                              "dataSource.advanced.statement_timeout_placeholder",
                            )}
                          />
                        </div>
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="sslmode">
                          {t("dataSource.advanced.sslmode")}
                        </Label>
                        <Select
                          value={formData.advanced_config.sslmode || ""}
                          onValueChange={(value) =>
                            handleAdvancedConfigChange("sslmode", value)
                          }
                        >
                          <SelectTrigger>
                            <SelectValue
                              placeholder={t(
                                "dataSource.advanced.select_sslmode",
                              )}
                            />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="disable">disable</SelectItem>
                            <SelectItem value="allow">allow</SelectItem>
                            <SelectItem value="prefer">prefer</SelectItem>
                            <SelectItem value="require">require</SelectItem>
                            <SelectItem value="verify-ca">verify-ca</SelectItem>
                            <SelectItem value="verify-full">
                              verify-full
                            </SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="sslcert">
                          {t("dataSource.advanced.sslcert")}
                        </Label>
                        <Input
                          id="sslcert"
                          value={formData.advanced_config.sslcert || ""}
                          onChange={(e) =>
                            handleAdvancedConfigChange(
                              "sslcert",
                              e.target.value,
                            )
                          }
                          placeholder={t(
                            "dataSource.advanced.sslcert_placeholder",
                          )}
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label htmlFor="sslkey">
                            {t("dataSource.advanced.sslkey")}
                          </Label>
                          <Input
                            id="sslkey"
                            value={formData.advanced_config.sslkey || ""}
                            onChange={(e) =>
                              handleAdvancedConfigChange(
                                "sslkey",
                                e.target.value,
                              )
                            }
                            placeholder={t(
                              "dataSource.advanced.sslkey_placeholder",
                            )}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="sslrootcert">
                            {t("dataSource.advanced.sslrootcert")}
                          </Label>
                          <Input
                            id="sslrootcert"
                            value={formData.advanced_config.sslrootcert || ""}
                            onChange={(e) =>
                              handleAdvancedConfigChange(
                                "sslrootcert",
                                e.target.value,
                              )
                            }
                            placeholder={t(
                              "dataSource.advanced.sslrootcert_placeholder",
                            )}
                          />
                        </div>
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="application_name">
                          {t("dataSource.advanced.application_name")}
                        </Label>
                        <Input
                          id="application_name"
                          value={
                            formData.advanced_config.application_name || ""
                          }
                          onChange={(e) =>
                            handleAdvancedConfigChange(
                              "application_name",
                              e.target.value,
                            )
                          }
                          placeholder={t(
                            "dataSource.advanced.application_name_placeholder",
                          )}
                        />
                      </div>
                    </>
                  )}

                  {/* Hive Advanced Config */}
                  {formData.type === "hive" && (
                    <>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label htmlFor="transport_mode">
                            {t("dataSource.advanced.transport_mode")}
                          </Label>
                          <Select
                            value={
                              formData.advanced_config.transport_mode || ""
                            }
                            onValueChange={(value) =>
                              handleAdvancedConfigChange(
                                "transport_mode",
                                value,
                              )
                            }
                          >
                            <SelectTrigger>
                              <SelectValue
                                placeholder={t(
                                  "dataSource.advanced.select_transport_mode",
                                )}
                              />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="binary">binary</SelectItem>
                              <SelectItem value="http">http</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="auth_mechanism">
                            {t("dataSource.advanced.auth_mechanism")}
                          </Label>
                          <Select
                            value={
                              formData.advanced_config.auth_mechanism || ""
                            }
                            onValueChange={(value) =>
                              handleAdvancedConfigChange(
                                "auth_mechanism",
                                value,
                              )
                            }
                          >
                            <SelectTrigger>
                              <SelectValue
                                placeholder={t(
                                  "dataSource.advanced.select_auth_mechanism",
                                )}
                              />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="NONE">NONE</SelectItem>
                              <SelectItem value="KERBEROS">KERBEROS</SelectItem>
                              <SelectItem value="LDAP">LDAP</SelectItem>
                              <SelectItem value="PAM">PAM</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <input
                          id="ssl_enabled"
                          type="checkbox"
                          checked={
                            formData.advanced_config.ssl_enabled || false
                          }
                          onChange={(e) =>
                            handleAdvancedConfigChange(
                              "ssl_enabled",
                              e.target.checked,
                            )
                          }
                          className="h-4 w-4"
                        />
                        <Label htmlFor="ssl_enabled">
                          {t("dataSource.advanced.ssl_enabled")}
                        </Label>
                      </div>
                    </>
                  )}

                  {/* Neo4j Advanced Config */}
                  {formData.type === "neo4j" && (
                    <>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label htmlFor="max_connection_pool_size">
                            {t("dataSource.advanced.max_connection_pool_size")}
                          </Label>
                          <Input
                            id="max_connection_pool_size"
                            type="number"
                            value={
                              formData.advanced_config
                                .max_connection_pool_size || ""
                            }
                            onChange={(e) =>
                              handleAdvancedConfigChange(
                                "max_connection_pool_size",
                                e.target.value
                                  ? parseInt(e.target.value)
                                  : undefined,
                              )
                            }
                            placeholder={t(
                              "dataSource.advanced.max_connection_pool_size_placeholder",
                            )}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="max_connection_lifetime">
                            {t("dataSource.advanced.max_connection_lifetime")}
                          </Label>
                          <Input
                            id="max_connection_lifetime"
                            type="number"
                            value={
                              formData.advanced_config
                                .max_connection_lifetime || ""
                            }
                            onChange={(e) =>
                              handleAdvancedConfigChange(
                                "max_connection_lifetime",
                                e.target.value
                                  ? parseInt(e.target.value)
                                  : undefined,
                              )
                            }
                            placeholder={t(
                              "dataSource.advanced.max_connection_lifetime_placeholder",
                            )}
                          />
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label htmlFor="connection_acquisition_timeout">
                            {t(
                              "dataSource.advanced.connection_acquisition_timeout",
                            )}
                          </Label>
                          <Input
                            id="connection_acquisition_timeout"
                            type="number"
                            value={
                              formData.advanced_config
                                .connection_acquisition_timeout || ""
                            }
                            onChange={(e) =>
                              handleAdvancedConfigChange(
                                "connection_acquisition_timeout",
                                e.target.value
                                  ? parseInt(e.target.value)
                                  : undefined,
                              )
                            }
                            placeholder={t(
                              "dataSource.advanced.connection_acquisition_timeout_placeholder",
                            )}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="connection_timeout">
                            {t("dataSource.advanced.connection_timeout")}
                          </Label>
                          <Input
                            id="connection_timeout"
                            type="number"
                            value={
                              formData.advanced_config.connection_timeout || ""
                            }
                            onChange={(e) =>
                              handleAdvancedConfigChange(
                                "connection_timeout",
                                e.target.value
                                  ? parseInt(e.target.value)
                                  : undefined,
                              )
                            }
                            placeholder={t(
                              "dataSource.advanced.connection_timeout_placeholder",
                            )}
                          />
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label htmlFor="trust">
                            {t("dataSource.advanced.trust")}
                          </Label>
                          <Select
                            value={formData.advanced_config.trust || ""}
                            onValueChange={(value) =>
                              handleAdvancedConfigChange("trust", value)
                            }
                          >
                            <SelectTrigger>
                              <SelectValue
                                placeholder={t(
                                  "dataSource.advanced.select_trust",
                                )}
                              />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="TRUST_ALL_CERTIFICATES">
                                TRUST_ALL_CERTIFICATES
                              </SelectItem>
                              <SelectItem value="TRUST_SYSTEM_CA_SIGNED_CERTIFICATES">
                                TRUST_SYSTEM_CA_SIGNED_CERTIFICATES
                              </SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="max_retry_time">
                            {t("dataSource.advanced.max_retry_time")}
                          </Label>
                          <Input
                            id="max_retry_time"
                            type="number"
                            value={
                              formData.advanced_config.max_retry_time || ""
                            }
                            onChange={(e) =>
                              handleAdvancedConfigChange(
                                "max_retry_time",
                                e.target.value
                                  ? parseInt(e.target.value)
                                  : undefined,
                              )
                            }
                            placeholder={t(
                              "dataSource.advanced.max_retry_time_placeholder",
                            )}
                          />
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <input
                          id="encrypted"
                          type="checkbox"
                          checked={formData.advanced_config.encrypted || false}
                          onChange={(e) =>
                            handleAdvancedConfigChange(
                              "encrypted",
                              e.target.checked,
                            )
                          }
                          className="h-4 w-4"
                        />
                        <Label htmlFor="encrypted">
                          {t("dataSource.advanced.encrypted")}
                        </Label>
                      </div>
                    </>
                  )}

                  {/* Kafka Advanced Config */}
                  {formData.type === "kafka" && (
                    <>
                      <div className="space-y-2">
                        <Label htmlFor="security_protocol">
                          {t("dataSource.advanced.security_protocol")}
                        </Label>
                        <Select
                          value={
                            formData.advanced_config.security_protocol || ""
                          }
                          onValueChange={(value) =>
                            handleAdvancedConfigChange(
                              "security_protocol",
                              value,
                            )
                          }
                        >
                          <SelectTrigger>
                            <SelectValue
                              placeholder={t(
                                "dataSource.advanced.select_security_protocol",
                              )}
                            />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="PLAINTEXT">PLAINTEXT</SelectItem>
                            <SelectItem value="SASL_PLAINTEXT">
                              SASL_PLAINTEXT
                            </SelectItem>
                            <SelectItem value="SSL">SSL</SelectItem>
                            <SelectItem value="SASL_SSL">SASL_SSL</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="sasl_mechanism">
                          {t("dataSource.advanced.sasl_mechanism")}
                        </Label>
                        <Select
                          value={formData.advanced_config.sasl_mechanism || ""}
                          onValueChange={(value) =>
                            handleAdvancedConfigChange("sasl_mechanism", value)
                          }
                        >
                          <SelectTrigger>
                            <SelectValue
                              placeholder={t(
                                "dataSource.advanced.select_sasl_mechanism",
                              )}
                            />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="PLAIN">PLAIN</SelectItem>
                            <SelectItem value="SCRAM-SHA-256">
                              SCRAM-SHA-256
                            </SelectItem>
                            <SelectItem value="SCRAM-SHA-512">
                              SCRAM-SHA-512
                            </SelectItem>
                            <SelectItem value="GSSAPI">GSSAPI</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="sasl_username">
                          {t("dataSource.advanced.sasl_username")}
                        </Label>
                        <Input
                          id="sasl_username"
                          value={formData.advanced_config.sasl_username || ""}
                          onChange={(e) =>
                            handleAdvancedConfigChange(
                              "sasl_username",
                              e.target.value,
                            )
                          }
                          placeholder={t(
                            "dataSource.advanced.sasl_username_placeholder",
                          )}
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="sasl_password">
                          {t("dataSource.advanced.sasl_password")}
                        </Label>
                        <Input
                          id="sasl_password"
                          type="password"
                          value={formData.advanced_config.sasl_password || ""}
                          onChange={(e) =>
                            handleAdvancedConfigChange(
                              "sasl_password",
                              e.target.value,
                            )
                          }
                          placeholder={t(
                            "dataSource.advanced.sasl_password_placeholder",
                          )}
                        />
                      </div>
                    </>
                  )}

                  {/* Flink Advanced Config */}
                  {formData.type === "flink" && (
                    <>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label htmlFor="connection_timeout">
                            {t("dataSource.advanced.connection_timeout")}
                          </Label>
                          <Input
                            id="connection_timeout"
                            type="number"
                            value={
                              formData.advanced_config.connection_timeout || ""
                            }
                            onChange={(e) =>
                              handleAdvancedConfigChange(
                                "connection_timeout",
                                e.target.value
                                  ? parseInt(e.target.value)
                                  : undefined,
                              )
                            }
                            placeholder={t(
                              "dataSource.advanced.connection_timeout_placeholder",
                            )}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="request_timeout">
                            {t("dataSource.advanced.request_timeout")}
                          </Label>
                          <Input
                            id="request_timeout"
                            type="number"
                            value={
                              formData.advanced_config.request_timeout || ""
                            }
                            onChange={(e) =>
                              handleAdvancedConfigChange(
                                "request_timeout",
                                e.target.value
                                  ? parseInt(e.target.value)
                                  : undefined,
                              )
                            }
                            placeholder={t(
                              "dataSource.advanced.request_timeout_placeholder",
                            )}
                          />
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <input
                          id="ssl_enabled"
                          type="checkbox"
                          checked={
                            formData.advanced_config.ssl_enabled || false
                          }
                          onChange={(e) =>
                            handleAdvancedConfigChange(
                              "ssl_enabled",
                              e.target.checked,
                            )
                          }
                          className="h-4 w-4"
                        />
                        <Label htmlFor="ssl_enabled">
                          {t("dataSource.advanced.ssl_enabled")}
                        </Label>
                      </div>
                      <div className="flex items-center space-x-2">
                        <input
                          id="ssl_verify_cert"
                          type="checkbox"
                          checked={
                            formData.advanced_config.ssl_verify_cert || false
                          }
                          onChange={(e) =>
                            handleAdvancedConfigChange(
                              "ssl_verify_cert",
                              e.target.checked,
                            )
                          }
                          className="h-4 w-4"
                        />
                        <Label htmlFor="ssl_verify_cert">
                          {t("dataSource.advanced.ssl_verify_cert")}
                        </Label>
                      </div>
                    </>
                  )}
                </div>
              </AccordionContent>
            </AccordionItem>
          </Accordion>
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
