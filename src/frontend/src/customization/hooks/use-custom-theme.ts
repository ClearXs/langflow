// Custom Hook to manage theme logic

import { useEffect, useState } from "react";
import { useDarkStore } from "@/stores/darkStore";

const useTheme = () => {
  const [systemTheme, setSystemTheme] = useState(false);

  // ✅ 修复: 使用稳定的选择器
  const setDark = useDarkStore((state) => state.setDark);
  const dark = useDarkStore((state) => state.dark);

  const handleSystemTheme = () => {
    if (typeof window !== "undefined") {
      const systemDarkMode = window.matchMedia(
        "(prefers-color-scheme: dark)",
      ).matches;
      setDark(systemDarkMode);
    }
  };

  // ✅ 修复: 添加 setDark 到依赖项
  useEffect(() => {
    const themePreference = localStorage.getItem("themePreference");
    if (themePreference === "light") {
      setDark(false);
      setSystemTheme(false);
    } else if (themePreference === "dark") {
      setDark(true);
      setSystemTheme(false);
    } else {
      // Default to system theme
      setSystemTheme(true);
      handleSystemTheme();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [setDark]);

  // ✅ 修复: 添加 setDark 到依赖项
  useEffect(() => {
    if (systemTheme && typeof window !== "undefined") {
      const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
      const handleChange = (e) => {
        setDark(e.matches);
      };
      mediaQuery.addEventListener("change", handleChange);
      return () => {
        mediaQuery.removeEventListener("change", handleChange);
      };
    }
  }, [systemTheme, setDark]);

  const setThemePreference = (theme) => {
    if (theme === "light") {
      setDark(false);
      setSystemTheme(false);
    } else if (theme === "dark") {
      setDark(true);
      setSystemTheme(false);
    } else {
      setSystemTheme(true);
      handleSystemTheme();
    }
    localStorage.setItem("themePreference", theme);
  };

  return { systemTheme, dark, setThemePreference };
};

export default useTheme;
