import { Badge } from "@/components/ui/badge";
import { statusLabel, statusTone, type StatusTone } from "../statuses";

const TONE_CLASSES: Record<StatusTone, string> = {
  neutral: "",
  info: "border-sky-200 bg-sky-50 text-sky-800",
  progress: "border-amber-200 bg-amber-50 text-amber-800",
  attention: "border-violet-200 bg-violet-50 text-violet-800",
  success: "border-emerald-200 bg-emerald-50 text-emerald-800",
  muted: "border-zinc-200 bg-white text-zinc-500",
};

// Shows an order status as a tinted pill, with a neutral pill for a status this client does not know.
export function StatusBadge({ status }: { status: string }) {
  return <Badge className={TONE_CLASSES[statusTone(status)]}>{statusLabel(status)}</Badge>;
}
