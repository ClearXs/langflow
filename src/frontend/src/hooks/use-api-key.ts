import { useCallback, useState } from "react";
import useAlertStore from "@/stores/alertStore";
import useAuthStore from "@/stores/authStore";

interface UseApiKeyReturn {
  apiKey: string | null;
  copied: boolean;
  copyToClipboard: () => Promise<void>;
}

export function useApiKey(): UseApiKeyReturn {
  const [copied, setCopied] = useState(false);
  const apiKey = useAuthStore((state) => state.accessToken);
  const setErrorData = useAlertStore((state) => state.setErrorData);
  const setSuccessData = useAlertStore((state) => state.setSuccessData);

  const fallbackCopyTextToClipboard = (text: string) => {
    const textArea = document.createElement("textarea");
    textArea.value = text;

    // Avoid scrolling to bottom
    textArea.style.top = "0";
    textArea.style.left = "0";
    textArea.style.position = "fixed";
    textArea.style.opacity = "0";

    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    try {
      const successful = document.execCommand("copy");
      document.body.removeChild(textArea);

      if (successful) {
        setCopied(true);
        setSuccessData({
          title: "API key copied to clipboard",
        });

        setTimeout(() => {
          setCopied(false);
        }, 2000);
      } else {
        setErrorData({
          title: "Failed to copy API key",
        });
      }
    } catch (err) {
      console.error("Fallback: Oops, unable to copy", err);
      document.body.removeChild(textArea);
      setErrorData({
        title: "Failed to copy API key",
      });
    }
  };

  const copyToClipboard = useCallback(async () => {
    if (!apiKey) return;

    try {
      if (navigator.clipboard && window.isSecureContext) {
        // Use Clipboard API if available and in secure context
        await navigator.clipboard.writeText(apiKey);
        setCopied(true);
        setSuccessData({
          title: "API key copied to clipboard",
        });

        setTimeout(() => {
          setCopied(false);
        }, 2000);
      } else {
        // Fallback for non-secure contexts or browsers without clipboard API
        fallbackCopyTextToClipboard(apiKey);
      }
    } catch (err) {
      console.error("Failed to copy:", err);
      setErrorData({
        title: "Failed to copy API key",
      });
    }
  }, [apiKey, setErrorData, setSuccessData]);

  return {
    apiKey,
    copied,
    copyToClipboard,
  };
}
