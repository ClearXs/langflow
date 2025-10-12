import { useTranslation } from "react-i18next";
import TimeoutErrorComponent from "@/components/common/timeoutErrorComponent";
import CustomFetchErrorComponent from "@/customization/components/custom-fetch-error-component";

export function GenericErrorComponent({ healthCheckTimeout, fetching, retry }) {
  const { t } = useTranslation();

  switch (healthCheckTimeout) {
    case "serverDown":
      return (
        <CustomFetchErrorComponent
          description={t("constants.error.fetchDescription")}
          message={t("constants.error.fetch")}
          openModal={true}
          setRetry={retry}
          isLoadingHealth={fetching}
        ></CustomFetchErrorComponent>
      );
    case "timeout":
      return (
        <TimeoutErrorComponent
          description={t("constants.error.timeout")}
          message={t("constants.error.timeoutDescription")}
          openModal={true}
          setRetry={retry}
          isLoadingHealth={fetching}
        ></TimeoutErrorComponent>
      );
    default:
      return <></>;
  }
}
