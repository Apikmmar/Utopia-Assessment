import { Button } from "@/components/ui/button";
import { failureMessage } from "@/lib/failure-message";
import { formatBytes, isPreviewable } from "../attachments";
import { useAttachments } from "../queries";
import type { Attachment } from "../schemas";

const KIND_LABELS: Record<string, string> = { completion: "Job files", receipt: "Receipt" };

// Returns a view link only when it is an https URL, so an unexpected value is never rendered as a link.
function safeViewUrl(attachment: Attachment) {
  return attachment.viewUrl && attachment.viewUrl.startsWith("https://") ? attachment.viewUrl : null;
}

// One uploaded file: a thumbnail for JPEG, PNG, and WebP, and a link for HEIC, video, and PDF.
function AttachmentItem({ attachment }: { attachment: Attachment }) {
  const url = safeViewUrl(attachment);
  if (url && isPreviewable(attachment.contentType)) {
    return (
      <li>
        <a href={url} target="_blank" rel="noopener noreferrer" className="block overflow-hidden rounded-lg border border-border">
          <img src={url} alt={attachment.fileName} loading="lazy" className="aspect-square w-full object-cover" />
        </a>
      </li>
    );
  }
  return (
    <li className="col-span-2 sm:col-span-3">
      {url ? (
        <a href={url} target="_blank" rel="noopener noreferrer" className="inline-flex min-h-11 items-center gap-2 text-sm font-medium underline underline-offset-4">
          {attachment.fileName}
          <span className="text-xs font-normal text-muted no-underline">· {formatBytes(attachment.sizeBytes)}</span>
        </a>
      ) : (
        <span className="text-sm text-muted">{attachment.fileName} (not available)</span>
      )}
    </li>
  );
}

// The uploaded files of an order grouped by kind, with view links that expire after a few minutes.
export function AttachmentList({ orderId }: { orderId: string }) {
  const attachments = useAttachments(orderId);
  if (attachments.isPending) {
    return (
      <p role="status" className="text-sm text-muted">
        Loading files…
      </p>
    );
  }
  if (attachments.isError) {
    return (
      <div role="alert" className="flex items-center gap-3 text-sm text-danger">
        <p>{failureMessage(attachments.error, "We could not load the files.")}</p>
        <Button variant="outline" onClick={() => void attachments.refetch()}>
          Retry
        </Button>
      </div>
    );
  }
  const uploaded = attachments.data.filter((attachment) => attachment.status === "uploaded");
  if (uploaded.length === 0) return <p className="text-sm text-muted">No files yet.</p>;
  return (
    <div className="flex flex-col gap-4">
      {Object.entries(KIND_LABELS).map(([kind, title]) => {
        const group = uploaded.filter((attachment) => attachment.kind === kind);
        if (group.length === 0) return null;
        return (
          <div key={kind} className="flex flex-col gap-2">
            <h3 className="text-xs font-medium text-muted">{title}</h3>
            <ul aria-label={title} className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {group.map((attachment) => (
                <AttachmentItem key={attachment.attachmentId} attachment={attachment} />
              ))}
            </ul>
          </div>
        );
      })}
    </div>
  );
}
