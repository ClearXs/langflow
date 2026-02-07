import { format } from "date-fns";
import {
  Calendar as CalendarIcon,
  Clock,
  Edit,
  Loader2,
  Plus,
  RefreshCw,
  Trash2,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
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
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  useDeleteConnector,
  useGetConnectorsQuery,
  usePostIndexConnector,
  usePutUpdateConnector,
} from "@/controllers/API/queries/connectors";
import { cn } from "@/utils/utils";

export default function ConnectorsManagePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { spaceId } = useParams<{ spaceId: string }>();
  const today = new Date();

  // API hooks
  const {
    data: connectors = [],
    isLoading,
    error,
  } = useGetConnectorsQuery(
    { enabled: !!spaceId },
    { search_space_id: Number(spaceId) },
  );

  const { mutateAsync: deleteConnector } = useDeleteConnector();
  const { mutateAsync: indexConnector } = usePostIndexConnector();
  const { mutateAsync: updateConnector } = usePutUpdateConnector();

  // State
  const [connectorToDelete, setConnectorToDelete] = useState<number | null>(
    null,
  );
  const [indexingConnectorId, setIndexingConnectorId] = useState<number | null>(
    null,
  );
  const [datePickerOpen, setDatePickerOpen] = useState(false);
  const [selectedConnectorForIndexing, setSelectedConnectorForIndexing] =
    useState<number | null>(null);
  const [startDate, setStartDate] = useState<Date | undefined>(undefined);
  const [endDate, setEndDate] = useState<Date | undefined>(undefined);

  // Periodic indexing state
  const [periodicDialogOpen, setPeriodicDialogOpen] = useState(false);
  const [selectedConnectorForPeriodic, setSelectedConnectorForPeriodic] =
    useState<number | null>(null);
  const [periodicEnabled, setPeriodicEnabled] = useState(false);
  const [frequencyMinutes, setFrequencyMinutes] = useState<string>("1440");
  const [customFrequency, setCustomFrequency] = useState<string>("");
  const [isSavingPeriodic, setIsSavingPeriodic] = useState(false);

  useEffect(() => {
    if (error) {
      toast.error(t("connectors.manage.failed_load"));
      console.error("Error fetching connectors:", error);
    }
  }, [error, t]);

  // Helper function to format date with time
  const formatDateTime = (dateString: string | null): string => {
    if (!dateString) return t("connectors.manage.never");

    const date = new Date(dateString);
    return new Intl.DateTimeFormat("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  };

  // Handle connector deletion
  const handleDeleteConnector = async () => {
    if (connectorToDelete === null || !spaceId) return;

    try {
      await deleteConnector({
        connectorId: connectorToDelete,
        search_space_id: Number(spaceId),
      });
      toast.success(t("connectors.manage.delete_success"));
    } catch (error) {
      console.error("Error deleting connector:", error);
      toast.error(t("connectors.manage.delete_failed"));
    } finally {
      setConnectorToDelete(null);
    }
  };

  // Handle opening date picker for indexing
  const handleOpenDatePicker = (connectorId: number) => {
    setSelectedConnectorForIndexing(connectorId);
    setDatePickerOpen(true);
  };

  // Handle connector indexing with dates
  const handleIndexConnector = async () => {
    if (selectedConnectorForIndexing === null || !spaceId) return;

    setDatePickerOpen(false);

    try {
      setIndexingConnectorId(selectedConnectorForIndexing);
      const startDateStr = startDate ? format(startDate, "yyyy-MM-dd") : null;
      const endDateStr = endDate ? format(endDate, "yyyy-MM-dd") : null;

      await indexConnector({
        connectorId: selectedConnectorForIndexing,
        search_space_id: Number(spaceId),
        params: {
          start_date: startDateStr,
          end_date: endDateStr,
        },
      });
      toast.success(t("connectors.manage.indexing_started"));
    } catch (error) {
      console.error("Error indexing connector content:", error);
      toast.error(
        error instanceof Error
          ? error.message
          : t("connectors.manage.indexing_failed"),
      );
    } finally {
      setIndexingConnectorId(null);
      setSelectedConnectorForIndexing(null);
      setStartDate(undefined);
      setEndDate(undefined);
    }
  };

  // Handle indexing without date picker (for quick indexing)
  const handleQuickIndexConnector = async (connectorId: number) => {
    if (!spaceId) return;
    setIndexingConnectorId(connectorId);
    try {
      await indexConnector({
        connectorId: connectorId,
        search_space_id: Number(spaceId),
      });
      toast.success(t("connectors.manage.indexing_started"));
    } catch (error) {
      console.error("Error indexing connector content:", error);
      toast.error(
        error instanceof Error
          ? error.message
          : t("connectors.manage.indexing_failed"),
      );
    } finally {
      setIndexingConnectorId(null);
    }
  };

  // Handle opening periodic indexing dialog
  const handleOpenPeriodicDialog = (connectorId: number) => {
    const connector = connectors.find((c) => c.id === connectorId);
    if (!connector) return;

    setSelectedConnectorForPeriodic(connectorId);
    setPeriodicEnabled(connector.is_periodic || false);
    setPeriodicDialogOpen(true);
  };

  // Handle saving periodic indexing configuration
  const handleSavePeriodicIndexing = async () => {
    if (selectedConnectorForPeriodic === null) return;

    const connector = connectors.find(
      (c) => c.id === selectedConnectorForPeriodic,
    );
    if (!connector) return;

    setIsSavingPeriodic(true);
    try {
      await updateConnector({
        connectorId: selectedConnectorForPeriodic,
        data: {
          is_periodic: periodicEnabled,
        },
      });

      toast.success(
        periodicEnabled
          ? t("connectors.manage.periodic_enabled")
          : t("connectors.manage.periodic_disabled"),
      );
      setPeriodicDialogOpen(false);
    } catch (error) {
      console.error("Error updating periodic indexing:", error);
      toast.error(
        error instanceof Error
          ? error.message
          : t("connectors.manage.periodic_update_failed"),
      );
    } finally {
      setIsSavingPeriodic(false);
      setSelectedConnectorForPeriodic(null);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Connectors Header */}
      <div className="border-b px-6 py-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold">
              {t("connectors.manage.title")}
            </h2>
            <p className="text-sm text-muted-foreground">
              {t("connectors.manage.subtitle")}
            </p>
          </div>
          <Button
            onClick={() =>
              navigate(`/spaces/${spaceId}/sources/add?tab=connectors`)
            }
          >
            <Plus className="mr-2 h-4 w-4" />
            {t("connectors.manage.add_connector")}
          </Button>
        </div>
      </div>

      {/* Connectors Content */}
      <div className="flex-1 overflow-auto p-6">
        {isLoading ? (
          <div className="flex justify-center py-8">
            <div className="animate-pulse text-center">
              <div className="h-6 w-32 bg-muted rounded mx-auto mb-2"></div>
              <div className="h-4 w-48 bg-muted rounded mx-auto"></div>
            </div>
          </div>
        ) : connectors.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center py-20 px-8">
            <div className="rounded-full bg-muted p-6 mb-6">
              <Plus className="h-12 w-12 text-muted-foreground" />
            </div>
            <h3 className="text-xl font-semibold mb-3">
              {t("connectors.manage.no_connectors")}
            </h3>
            <p className="text-muted-foreground text-center max-w-md mb-8 text-base">
              {t("connectors.manage.no_connectors_desc")}
            </p>
            <Button
              onClick={() =>
                navigate(`/spaces/${spaceId}/sources/add?tab=connectors`)
              }
              size="lg"
            >
              <Plus className="mr-2 h-5 w-5" />
              {t("connectors.manage.add_first")}
            </Button>
          </div>
        ) : (
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("connectors.manage.name")}</TableHead>
                  <TableHead>{t("connectors.manage.type")}</TableHead>
                  <TableHead>{t("connectors.manage.last_indexed")}</TableHead>
                  <TableHead>{t("connectors.manage.periodic")}</TableHead>
                  <TableHead className="text-right">
                    {t("connectors.manage.actions")}
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {connectors.map((connector) => (
                  <TableRow key={connector.id}>
                    <TableCell className="font-medium">
                      {connector.name}
                    </TableCell>
                    <TableCell>{connector.connector_type}</TableCell>
                    <TableCell>
                      {formatDateTime(connector.last_indexed_at)}
                    </TableCell>
                    <TableCell>
                      {connector.is_periodic ? (
                        <div className="flex items-center gap-1 text-green-600 dark:text-green-400">
                          <Clock className="h-4 w-4" />
                          <span className="text-sm font-medium">
                            {t("connectors.manage.enabled")}
                          </span>
                        </div>
                      ) : (
                        <span className="text-sm text-muted-foreground">
                          {t("connectors.manage.disabled")}
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() =>
                                  handleOpenDatePicker(connector.id)
                                }
                                disabled={indexingConnectorId === connector.id}
                              >
                                {indexingConnectorId === connector.id ? (
                                  <RefreshCw className="h-4 w-4 animate-spin" />
                                ) : (
                                  <CalendarIcon className="h-4 w-4" />
                                )}
                                <span className="sr-only">
                                  {t("connectors.manage.index_date_range")}
                                </span>
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>
                              <p>{t("connectors.manage.index_date_range")}</p>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() =>
                                  handleQuickIndexConnector(connector.id)
                                }
                                disabled={indexingConnectorId === connector.id}
                              >
                                {indexingConnectorId === connector.id ? (
                                  <RefreshCw className="h-4 w-4 animate-spin" />
                                ) : (
                                  <RefreshCw className="h-4 w-4" />
                                )}
                                <span className="sr-only">
                                  {t("connectors.manage.quick_index")}
                                </span>
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>
                              <p>{t("connectors.manage.quick_index_auto")}</p>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() =>
                                  handleOpenPeriodicDialog(connector.id)
                                }
                              >
                                <Clock className="h-4 w-4" />
                                <span className="sr-only">
                                  {t("connectors.manage.configure_periodic")}
                                </span>
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>
                              <p>{t("connectors.manage.configure_periodic")}</p>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button
                              variant="outline"
                              size="sm"
                              className="hover:text-destructive hover:border-destructive"
                              onClick={() => setConnectorToDelete(connector.id)}
                            >
                              <Trash2 className="h-4 w-4" />
                              <span className="sr-only">
                                {t("common.delete")}
                              </span>
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>
                                {t("connectors.manage.delete_connector")}
                              </AlertDialogTitle>
                              <AlertDialogDescription>
                                {t("connectors.manage.delete_confirm")}
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel
                                onClick={() => setConnectorToDelete(null)}
                              >
                                {t("common.cancel")}
                              </AlertDialogCancel>
                              <AlertDialogAction
                                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                                onClick={handleDeleteConnector}
                              >
                                {t("common.delete")}
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>

      {/* Date Picker Dialog */}
      <Dialog open={datePickerOpen} onOpenChange={setDatePickerOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>
              {t("connectors.manage.select_date_range")}
            </DialogTitle>
            <DialogDescription>
              {t("connectors.manage.select_date_range_desc")}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="start-date">
                  {t("connectors.manage.start_date")}
                </Label>
                <Popover>
                  <PopoverTrigger asChild>
                    <Button
                      id="start-date"
                      variant="outline"
                      className={cn(
                        "w-full justify-start text-left font-normal",
                        !startDate && "text-muted-foreground",
                      )}
                    >
                      <CalendarIcon className="mr-2 h-4 w-4" />
                      {startDate
                        ? format(startDate, "PPP")
                        : t("connectors.manage.pick_date")}
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-auto p-0" align="start">
                    <Calendar
                      mode="single"
                      selected={startDate}
                      onSelect={setStartDate}
                    />
                  </PopoverContent>
                </Popover>
              </div>
              <div className="space-y-2">
                <Label htmlFor="end-date">
                  {t("connectors.manage.end_date")}
                </Label>
                <Popover>
                  <PopoverTrigger asChild>
                    <Button
                      id="end-date"
                      variant="outline"
                      className={cn(
                        "w-full justify-start text-left font-normal",
                        !endDate && "text-muted-foreground",
                      )}
                    >
                      <CalendarIcon className="mr-2 h-4 w-4" />
                      {endDate
                        ? format(endDate, "PPP")
                        : t("connectors.manage.pick_date")}
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-auto p-0" align="start">
                    <Calendar
                      mode="single"
                      selected={endDate}
                      onSelect={setEndDate}
                    />
                  </PopoverContent>
                </Popover>
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setStartDate(undefined);
                  setEndDate(undefined);
                }}
              >
                {t("connectors.manage.clear_dates")}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  const thirtyDaysAgo = new Date(today);
                  thirtyDaysAgo.setDate(today.getDate() - 30);
                  setStartDate(thirtyDaysAgo);
                  setEndDate(today);
                }}
              >
                {t("connectors.manage.last_30_days")}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  const yearAgo = new Date(today);
                  yearAgo.setFullYear(today.getFullYear() - 1);
                  setStartDate(yearAgo);
                  setEndDate(today);
                }}
              >
                {t("connectors.manage.last_year")}
              </Button>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setDatePickerOpen(false);
                setSelectedConnectorForIndexing(null);
                setStartDate(undefined);
                setEndDate(undefined);
              }}
            >
              {t("common.cancel")}
            </Button>
            <Button onClick={handleIndexConnector}>
              {t("connectors.manage.start_indexing")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Periodic Indexing Configuration Dialog */}
      <Dialog open={periodicDialogOpen} onOpenChange={setPeriodicDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>
              {t("connectors.manage.configure_periodic")}
            </DialogTitle>
            <DialogDescription>
              {t("connectors.manage.configure_periodic_desc")}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-6 py-4">
            <div className="flex items-center justify-between space-x-2">
              <div className="space-y-0.5">
                <Label htmlFor="periodic-enabled" className="text-base">
                  {t("connectors.manage.enable_periodic")}
                </Label>
                <p className="text-sm text-muted-foreground">
                  {t("connectors.manage.enable_periodic_desc")}
                </p>
              </div>
              <Switch
                id="periodic-enabled"
                checked={periodicEnabled}
                onCheckedChange={setPeriodicEnabled}
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setPeriodicDialogOpen(false);
                setSelectedConnectorForPeriodic(null);
              }}
            >
              {t("common.cancel")}
            </Button>
            <Button
              onClick={handleSavePeriodicIndexing}
              disabled={isSavingPeriodic}
            >
              {isSavingPeriodic && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              {t("connectors.manage.save_configuration")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
