import { CircleCheck, EyeOff, ShieldX, TriangleAlert, type LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";
import type { Action } from "@/lib/types";

/** Colour is never the only signal: every decision also has an icon and a text label. */
export const DECISION: Record<Action, { label: string; icon: LucideIcon; badge: string; bar: string; meaning: string }> = {
  block: { label: "Block", icon: ShieldX, badge: "bg-block-soft text-block-fg border-block/30", bar: "bg-block", meaning: "Nothing is sent" },
  redact: { label: "Redact", icon: EyeOff, badge: "bg-redact-soft text-redact-fg border-redact/40", bar: "bg-redact", meaning: "Sent with values removed" },
  warn: { label: "Warn", icon: TriangleAlert, badge: "bg-warn-soft text-warn-fg border-warn/30", bar: "bg-warn", meaning: "Sent with a warning" },
  allow: { label: "Allow", icon: CircleCheck, badge: "bg-allow-soft text-allow-fg border-allow/30", bar: "bg-allow", meaning: "Sent unchanged" },
};

export function DecisionBadge({ action, size = "sm" }: { action: Action; size?: "sm" | "lg" }) {
  const d = DECISION[action];
  const Icon = d.icon;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border font-medium",
        size === "lg" ? "px-3 py-1 text-base" : "px-2 py-0.5 text-xs",
        d.badge,
      )}
    >
      <Icon className={size === "lg" ? "size-5" : "size-3.5"} aria-hidden="true" />
      {d.label}
    </span>
  );
}

const ACRONYMS: Record<string, string> = { ip: "IP", jwt: "JWT", aws: "AWS" };

/** "internal_ip" -> "Internal IP", "aws_access_key" -> "AWS access key". */
export const TYPE_LABEL = (t: string) => {
  const words = t.split("_").map((w) => ACRONYMS[w] ?? w);
  const text = words.join(" ");
  return text.charAt(0).toUpperCase() + text.slice(1);
};
