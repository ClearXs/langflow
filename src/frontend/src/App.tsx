import '@xyflow/react/dist/style.css';
import { Suspense, useEffect } from 'react';
import { RouterProvider } from 'react-router-dom';
import { LoadingPage } from './pages/LoadingPage';
import router from './routes';
import { useDarkStore } from './stores/darkStore';
import { useI18nStore } from './stores/i18nStore';
import { useTranslation } from 'react-i18next';

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
      i18n.changeLanguage(lang);
    }
  }, [lang]);

  return (
    <Suspense fallback={<LoadingPage />}>
      <RouterProvider router={router} />
    </Suspense>
  );
}
