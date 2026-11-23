"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BookOpenText, LayoutDashboard, ScanSearch, ShieldCheck } from "lucide-react";

import { ThemeToggle } from "@/components/theme-toggle";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Playground", icon: ScanSearch },
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/about", label: "How it works", icon: BookOpenText },
] as const;

function Brand() {
  return (
    <div className="flex items-center gap-3">
      <span className="grid size-9 place-items-center rounded-lg bg-primary text-primary-foreground">
        <ShieldCheck className="size-5" aria-hidden="true" />
      </span>
      <span className="leading-tight">
        <span className="block text-sm font-semibold">PromptGuard</span>
        <span className="block text-xs text-muted-foreground">DLP for AI prompts</span>
      </span>
    </div>
  );
}

function NavLinks({ orientation }: { orientation: "vertical" | "horizontal" }) {
  const pathname = usePathname();
  return (
    <ul className={cn("flex gap-1", orientation === "vertical" ? "flex-col" : "flex-row overflow-x-auto")}>
      {NAV.map(({ href, label, icon: Icon }) => {
        const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
        return (
          <li key={href} className={orientation === "horizontal" ? "shrink-0" : undefined}>
            <Link
              href={href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
            >
              <Icon className="size-4 max-sm:hidden" aria-hidden="true" />
              {label}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-dvh md:grid md:grid-cols-[16rem_minmax(0,1fr)]">
      <a
        href="#main"
        className="sr-only z-50 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground focus:not-sr-only focus:fixed focus:left-3 focus:top-3"
      >
        Skip to content
      </a>

      {/* Desktop sidebar */}
      <aside className="sticky top-0 hidden h-dvh flex-col border-r bg-sidebar p-4 md:flex">
        <Brand />
        <nav aria-label="Main" className="mt-8">
          <NavLinks orientation="vertical" />
        </nav>
        <div className="mt-auto space-y-3">
          <p className="rounded-lg border bg-muted/50 p-3 text-xs leading-relaxed text-muted-foreground">
            Working prototype. Not a replacement for enterprise DLP tools such as Microsoft Purview.
          </p>
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">Theme</span>
            <ThemeToggle />
          </div>
        </div>
      </aside>

      <div className="min-w-0">
        {/* Mobile header: brand and theme on top, nav as a scrollable row below. No drawer needed. */}
        <header className="sticky top-0 z-30 border-b bg-background/90 px-4 py-3 backdrop-blur md:hidden">
          <div className="flex items-center justify-between">
            <Brand />
            <ThemeToggle />
          </div>
          <nav aria-label="Main" className="-mx-1 mt-3">
            <NavLinks orientation="horizontal" />
          </nav>
        </header>

        <main id="main" tabIndex={-1} className="mx-auto w-full max-w-5xl px-4 py-6 outline-none md:px-8 md:py-10">
          {children}
        </main>
      </div>
    </div>
  );
}
