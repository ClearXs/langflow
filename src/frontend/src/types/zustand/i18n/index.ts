export type Language = 'en' | 'zh'

export type I18nType = {
  lang: Language;
  setLanguage: (lang:Language) => void
};
