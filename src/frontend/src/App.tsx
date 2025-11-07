import '@xyflow/react/dist/style.css';
import { Suspense, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { RouterProvider } from 'react-router-dom';
import DataSourceDialog from './components/datasourceDialogComponent';
import { TooltipProvider } from './components/ui/tooltip';
import { PostMessageProvider } from './contexts/postMessageContext';
import { LoadingPage } from './pages/LoadingPage';
import router from './routes';
import { useDarkStore } from './stores/darkStore';
import { useI18nStore } from './stores/i18nStore';
import type { StoredMessage } from './types/zustand/postMessage';

export default function App() {
  const dark = useDarkStore((state) => state.dark);
  const lang = useI18nStore((state) => state.lang);
  const { i18n } = useTranslation();

  useEffect(() => {
    if (!dark) {
      document.getElementById('body')!.classList.remove('dark');
    } else {
      document.getElementById('body')!.classList.add('dark');
    }
  }, [dark]);

  useEffect(() => {
    if (lang) {
      // i18n.changeLanguage(lang);
    }
  }, [lang]);

  // Global postMessage handler for debugging/logging (optional)
  const handleGlobalMessage = (message: StoredMessage) => {
    // Log all postMessages in development
    // You can add global message handling logic here
    // For example: analytics, error tracking, etc.
  };

  return (
    <Suspense fallback={<LoadingPage />}>
      <PostMessageProvider
        options={{
          // Configure allowed origins for security
          // In production, specify your parent application domains
          allowedOrigins:
            process.env.NODE_ENV === 'production'
              ? [
                  // Add your production domains here
                  // "https://your-parent-domain.com",
                  // "*.trusted-domain.com"
                ]
              : [], // Allow all origins in development

          // Auto-cleanup old messages to prevent memory leaks
          autoCleanup: true,
          cleanupInterval: 5 * 60 * 1000, // 5 minutes
          maxMessageAge: 60 * 60 * 1000, // 1 hour

          // Enable listening by default
          enabled: true,
        }}
        onGlobalMessage={handleGlobalMessage}
      >
        <RouterProvider router={router} />
        <TooltipProvider>
          <DataSourceDialog />
        </TooltipProvider>
      </PostMessageProvider>
    </Suspense>
  );
}
