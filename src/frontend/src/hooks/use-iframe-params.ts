import { useMemo } from "react";

/**
 * Simple hook to check if app is running in an iframe
 *
 * @example
 * const isEmbedded = useIsEmbedded();
 * if (isEmbedded) {
 *   // Show embedded UI
 * }
 */
export const useIsEmbedded = (): boolean => {
  const ref = useUrlParam("ref");
  return useMemo(() => {
    try {
      return ref != undefined && ref === "datasense";
    } catch (e) {
      return false;
    }
  }, [ref]);
};

/**
 * Hook to get a specific URL parameter
 *
 * @example
 * const userId = useUrlParam("user_id");
 * const theme = useUrlParam("theme");
 */
export const useUrlParam = (paramName: string): string | null => {
  return useMemo(() => {
    const params = new URLSearchParams(window.location.search);
    const value = params.get(paramName);
    console.log(`[useUrlParam] ${paramName} = ${value}`);
    return value;
  }, [paramName]);
};
