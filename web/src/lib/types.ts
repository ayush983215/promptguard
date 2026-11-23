export type Action = "allow" | "warn" | "redact" | "block";

export type Finding = {
  type: string;
  action: Action;
  confidence: "high" | "low";
  masked: string;
};

export type CheckResult = {
  decision: Action;
  rule_decision: Action;
  explanation: string;
  /** Text that would be forwarded to the AI tool; null when the prompt is blocked. */
  text: string | null;
  findings: Finding[];
  agent: { used: boolean; tightened: boolean; loosen_attempt_ignored: boolean };
};

export type Stats = {
  decisions: Partial<Record<Action, number>>;
  top_types: [string, number][];
  repeated_values: [string, number][];
  agent_tightened: number;
  agent_loosen_attempts_blocked: number;
};

export type EventRow = {
  id: number;
  ts: number;
  user: string;
  decision: Action;
  rule_decision: Action;
  agent_tightened: number;
  agent_loosen_attempt: number;
  prompt_chars: number;
  n_findings: number;
  findings: { type: string; action: Action; confidence: string; masked: string }[];
};

export type Example = { label: string; prompt: string };
