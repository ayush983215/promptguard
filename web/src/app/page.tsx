import { PageHeader } from "@/components/page-header";
import { Playground } from "@/components/playground";

export default function Home() {
  return (
    <>
      <PageHeader
        title="Check a prompt before it leaves"
        description="PromptGuard scans text for credentials, card numbers and personal data, then decides whether to block it, redact it, or send it with a warning."
      />
      <Playground />
    </>
  );
}
