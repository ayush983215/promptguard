"use client";

import { Moon, Sun } from "lucide-react";

import { Button } from "@/components/ui/button";

/** Toggles the `dark` class on <html>. The initial value is set before paint by a script in layout.tsx. */
export function ThemeToggle() {
  function toggle() {
    const dark = document.documentElement.classList.toggle("dark");
    try {
      localStorage.setItem("pg-theme", dark ? "dark" : "light");
    } catch {
      /* storage can be blocked; the toggle still works for this visit */
    }
  }
  return (
    <Button type="button" variant="outline" size="icon" onClick={toggle} aria-label="Toggle light or dark theme">
      <Sun className="hidden size-4 dark:block" aria-hidden="true" />
      <Moon className="size-4 dark:hidden" aria-hidden="true" />
    </Button>
  );
}
