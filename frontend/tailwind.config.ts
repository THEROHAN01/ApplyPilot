import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["selector", '[data-theme="dark"]'],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)", surface: "var(--bg-surface)",
        "surface-hover": "var(--bg-surface-hover)",
        ink: "var(--ink)", "ink-soft": "var(--ink-soft)", "ink-mute": "var(--ink-mute)",
        rule: "var(--rule)", "rule-soft": "var(--rule-soft)",
        blueprint: "var(--blueprint)", "accent-hover": "var(--accent-hover)",
        "on-accent": "var(--on-accent)", warn: "var(--warn)",
        "blueprint-tint": "var(--blueprint-tint)",
        "blueprint-tint-strong": "var(--blueprint-tint-strong)",
      },
      borderRadius: { none: "0", DEFAULT: "0", sm: "0", md: "0", lg: "0", xl: "0", "2xl": "0", "3xl": "0", full: "0" },
      boxShadow: { hard: "3px 3px 0 var(--ink)", "hard-lg": "5px 5px 0 var(--ink)" },
      fontFamily: {
        display: ["var(--font-display)", "monospace"],
        body: ["var(--font-body)", "serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
