/**
 * Theme handling (FR-124…FR-127): light is the default, dark is a separately
 * designed palette, the user's choice is remembered — in localStorage for the
 * pre-login flash guard and on the user profile so it follows them across
 * devices. "" (system) falls back to the OS preference on first visit.
 */

export type ThemePreference = "" | "LIGHT" | "DARK";

export const THEME_STORAGE_KEY = "stock-tracker-theme";

/** Inline <head> script: applies the stored theme before first paint. */
export const THEME_BOOT_SCRIPT = `
(function () {
  try {
    var stored = localStorage.getItem("${THEME_STORAGE_KEY}");
    var dark =
      stored === "DARK" ||
      (!stored && window.matchMedia("(prefers-color-scheme: dark)").matches);
    if (dark) document.documentElement.classList.add("dark");
  } catch (e) {}
})();
`;

export function applyTheme(preference: ThemePreference) {
  const dark =
    preference === "DARK" ||
    (preference === "" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("dark", dark);
  try {
    if (preference === "") localStorage.removeItem(THEME_STORAGE_KEY);
    else localStorage.setItem(THEME_STORAGE_KEY, preference);
  } catch {
    /* storage unavailable — theme still applies for this page */
  }
}

export function isDarkActive(): boolean {
  return document.documentElement.classList.contains("dark");
}
