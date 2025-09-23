import { I18nType } from '@/types/zustand/i18n';
import { create } from 'zustand';

export const useI18nStore = create<I18nType>((set, get) => ({
  lang: (() => {
    const stored = window.localStorage.getItem('language');
    if (stored !== null) {
      return JSON.parse(stored);
    }
    const browserLanguage = navigator.language || navigator.languages[0];
    const detectedLanguage = browserLanguage.split('-')[0];
    return detectedLanguage;
  })(),

  setLanguage(lang) {
    window.localStorage.setItem('language', JSON.stringify(lang));
    set({ lang });
  },
}));
