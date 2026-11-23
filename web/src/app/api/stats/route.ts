import { backend, relay } from "@/lib/backend";

export async function GET() {
  return relay(() => backend("/stats", {}, true));
}
