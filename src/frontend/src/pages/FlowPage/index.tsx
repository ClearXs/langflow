import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useBlocker, useParams } from "react-router-dom";
import { SidebarProvider } from "@/components/ui/sidebar";
import { useGetFlow } from "@/controllers/API/queries/flows/use-get-flow";
import { useGetTypes } from "@/controllers/API/queries/flows/use-get-types";
import { ENABLE_NEW_SIDEBAR } from "@/customization/feature-flags";
import { useCustomNavigate } from "@/customization/hooks/use-custom-navigate";
import useSaveFlow from "@/hooks/flows/use-save-flow";
import { useUrlParam } from "@/hooks/use-iframe-params";
import { useIsMobile } from "@/hooks/use-mobile";
import { SaveChangesModal } from "@/modals/saveChangesModal";
import useAlertStore from "@/stores/alertStore";
import { useTypesStore } from "@/stores/typesStore";
import { customStringify } from "@/utils/reactflowUtils";
import useFlowStore from "../../stores/flowStore";
import useFlowsManagerStore from "../../stores/flowsManagerStore";
import {
  FlowSearchProvider,
  FlowSidebarComponent,
} from "./components/flowSidebarComponent";
import Page from "./components/PageComponent";

export default function FlowPage({ view }: { view?: boolean }): JSX.Element {
  const { t } = useTranslation();
  const types = useTypesStore((state) => state.types);

  // Detect stream parameter from URL
  const streamParam = useUrlParam("stream");
  const isPersistentStream = streamParam === "true";

  // Debug logging
  console.log("[FlowPage] streamParam =", streamParam, "isPersistentStream =", isPersistentStream);

  useGetTypes({
    enabled: Object.keys(types).length <= 0,
  });

  const setCurrentFlow = useFlowsManagerStore((state) => state.setCurrentFlow);
  const currentFlow = useFlowStore((state) => state.currentFlow);
  const currentSavedFlow = useFlowsManagerStore((state) => state.currentFlow);
  const setSuccessData = useAlertStore((state) => state.setSuccessData);
  const setIsPersistentStream = useFlowStore(
    (state) => state.setIsPersistentStream,
  );
  const setIsBuilding = useFlowStore((state) => state.setIsBuilding);
  const setStreamingJobId = useFlowStore((state) => state.setStreamingJobId);
  const [isLoading, setIsLoading] = useState(false);

  // Get flow ID from URL params
  const { id } = useParams();

  // Sync isPersistentStream to store when URL parameter changes
  useEffect(() => {
    setIsPersistentStream(isPersistentStream);
  }, [isPersistentStream, setIsPersistentStream]);

  // Check and restore streaming status on page load
  useEffect(() => {
    const checkAndRestoreStreamingStatus = async () => {
      // Only check if in persistent streaming mode
      if (!isPersistentStream) return;
      if (!id) return;

      try {
        const response = await fetch(`/api/v1/flows/${id}/status`);

        if (!response.ok) {
          console.error("Failed to check flow status");
          return;
        }

        const data = await response.json();
        const { is_running, job_id } = data;

        if (is_running && job_id) {
          console.log(
            `Restoring streaming status for flow ${id}, job ${job_id}`,
          );

          // Restore running state
          setIsBuilding(true);
          setStreamingJobId(job_id);

          // Optional: Reconnect to job events for real-time logs
          // This would require additional implementation
        }
      } catch (error) {
        console.error("Error checking flow status:", error);
      }
    };

    // Delay execution to ensure page is fully loaded
    const timeoutId = setTimeout(checkAndRestoreStreamingStatus, 500);

    return () => clearTimeout(timeoutId);
  }, [isPersistentStream, id, setIsBuilding, setStreamingJobId]);

  const changesNotSaved =
    customStringify(currentFlow) !== customStringify(currentSavedFlow) &&
    (currentFlow?.data?.nodes?.length ?? 0) > 0;

  const isBuilding = useFlowStore((state) => state.isBuilding);
  const isPersistentStreamStore = useFlowStore(
    (state) => state.isPersistentStream,
  );
  const blocker = useBlocker(
    (isPersistentStreamStore ? false : changesNotSaved) || isBuilding,
  );

  const setOnFlowPage = useFlowStore((state) => state.setOnFlowPage);
  const navigate = useCustomNavigate();
  const saveFlow = useSaveFlow();

  const flows = useFlowsManagerStore((state) => state.flows);
  const currentFlowId = useFlowsManagerStore((state) => state.currentFlowId);

  const updatedAt = currentSavedFlow?.updated_at;
  const autoSaving = useFlowsManagerStore((state) => state.autoSaving);
  const stopBuilding = useFlowStore((state) => state.stopBuilding);

  const { mutateAsync: getFlow } = useGetFlow();

  const handleSave = () => {
    let saving = true;
    let proceed = false;
    setTimeout(() => {
      saving = false;
      if (proceed) {
        blocker.proceed && blocker.proceed();
        setSuccessData({
          title: t("common.flowSavedSuccessfully"),
        });
      }
    }, 1200);
    saveFlow().then(() => {
      if (!autoSaving || saving === false) {
        blocker.proceed && blocker.proceed();
        setSuccessData({
          title: t("common.flowSavedSuccessfully"),
        });
      }
      proceed = true;
    });
  };

  const handleExit = () => {
    if (isBuilding) {
      // Do nothing, let the blocker handle it
    } else if (changesNotSaved) {
      if (blocker.proceed) blocker.proceed();
    } else {
      navigate("/all");
    }
  };

  useEffect(() => {
    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      // Persistent streaming flows don't block page exit
      if (!isPersistentStreamStore && (changesNotSaved || isBuilding)) {
        event.preventDefault();
        event.returnValue = ""; // Required for Chrome
      }
    };

    window.addEventListener("beforeunload", handleBeforeUnload);

    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };
  }, [changesNotSaved, isBuilding, isPersistentStreamStore]);

  // Set flow tab id
  useEffect(() => {
    const awaitgetTypes = async () => {
      if (flows && currentFlowId === "" && Object.keys(types).length > 0) {
        const isAnExistingFlow = flows.find((flow) => flow.id === id);

        if (!isAnExistingFlow) {
          navigate("/all");
          return;
        }

        const isAnExistingFlowId = isAnExistingFlow.id;

        await getFlowToAddToCanvas(isAnExistingFlowId);
      }
    };
    awaitgetTypes();
  }, [id, flows, currentFlowId, types]);

  useEffect(() => {
    setOnFlowPage(true);

    return () => {
      setOnFlowPage(false);
      console.warn(t("common.unmounting"));

      // Don't stop building in cleanup - this causes race conditions
      // Building should be stopped explicitly by user or handled by beforeunload

      setCurrentFlow(undefined);
    };
  }, [id]);

  useEffect(() => {
    if (
      blocker.state === "blocked" &&
      autoSaving &&
      changesNotSaved &&
      !isBuilding
    ) {
      handleSave();
    }
  }, [blocker.state, isBuilding]);

  useEffect(() => {
    if (blocker.state === "blocked") {
      if (isBuilding) {
        stopBuilding().catch((error) => {
          console.error("Error stopping building:", error);
        });
      } else if (!changesNotSaved) {
        blocker.proceed && blocker.proceed();
      }
    }
  }, [blocker.state, isBuilding]);

  const getFlowToAddToCanvas = async (id: string) => {
    const flow = await getFlow({ id: id });
    setCurrentFlow(flow);
  };

  const isMobile = useIsMobile();

  return (
    <>
      <div className="flow-page-positioning">
        {currentFlow && (
          <div className="flex h-full overflow-hidden">
            <SidebarProvider
              width="17.5rem"
              defaultOpen={!isMobile}
              segmentedSidebar={ENABLE_NEW_SIDEBAR}
            >
              <FlowSearchProvider>
                {!view && <FlowSidebarComponent isLoading={isLoading} />}
                <main className="flex w-full overflow-hidden">
                  <div className="h-full w-full">
                    <Page setIsLoading={setIsLoading} />
                  </div>
                </main>
              </FlowSearchProvider>
            </SidebarProvider>
          </div>
        )}
      </div>
      {blocker.state === "blocked" && (
        <>
          {!isBuilding && currentSavedFlow && (
            <SaveChangesModal
              onSave={handleSave}
              onCancel={() => blocker.reset?.()}
              onProceed={handleExit}
              flowName={currentSavedFlow.name}
              lastSaved={
                updatedAt
                  ? new Date(updatedAt).toLocaleString("en-US", {
                      hour: "numeric",
                      minute: "numeric",
                      second: "numeric",
                      month: "numeric",
                      day: "numeric",
                    })
                  : undefined
              }
              autoSave={autoSaving}
            />
          )}
        </>
      )}
    </>
  );
}
