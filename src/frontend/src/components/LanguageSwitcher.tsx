"use client";

import { Globe } from "lucide-react";
import { useTranslation } from "react-i18next";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useI18nStore } from "@/stores/i18nStore";

/**
 * Language switcher component
 * Allows users to change the application language
 * Persists preference in localStorage via i18nStore
 */
export function LanguageSwitcher() {
  const { i18n } = useTranslation();
  const lang = useI18nStore((state) => state.lang);
  const setLanguage = useI18nStore((state) => state.setLanguage);

  // Supported languages configuration
  const languages = [
    { code: "en" as const, name: "English", flag: "🇺🇸" },
    { code: "zh" as const, name: "简体中文", flag: "🇨🇳" },
  ];

  /**
   * Handle language change
   * Updates locale in store and i18next
   */
  const handleLanguageChange = (newLocale: string) => {
    setLanguage(newLocale);
    i18n.changeLanguage(newLocale);
  };

  const currentLanguage =
    languages.find((l) => l.code === lang) || languages[0];

  return (
    <Select value={lang || "en"} onValueChange={handleLanguageChange}>
      <SelectTrigger className="w-[160px]">
        <Globe className="mr-2 h-4 w-4" />
        <SelectValue>{currentLanguage.name}</SelectValue>
      </SelectTrigger>
      <SelectContent>
        {languages.map((language) => (
          <SelectItem key={language.code} value={language.code}>
            <span className="flex items-center gap-2">
              <span>{language.flag}</span>
              <span>{language.name}</span>
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
