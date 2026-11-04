import { useId, useRef } from "react";
import { Button } from "@/components/ui/button";
import { ATTACHMENT_LIMITS, formatBytes } from "../attachments";
import type { FileUploadState, UploadItem } from "../hooks/use-file-upload";

type FileUploaderProps = { upload: FileUploadState; label: string; hint?: string };

// Status line for one file: progress while uploading, done, or the failure reason.
function ItemStatus({ item }: { item: UploadItem }) {
  if (item.status === "uploading") {
    const percent = Math.round(item.progress * 100);
    return (
      <div className="flex items-center gap-2">
        <div role="progressbar" aria-label={`Uploading ${item.fileName}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent} className="h-1.5 w-full overflow-hidden rounded-full bg-subtle">
          <div className="h-full rounded-full bg-primary transition-[width]" style={{ width: `${percent}%` }} />
        </div>
        <span className="w-10 text-right text-xs text-muted tabular-nums">{percent}%</span>
      </div>
    );
  }
  if (item.status === "failed") {
    return (
      <p role="alert" className="text-xs text-danger">
        {item.error}
      </p>
    );
  }
  return <p className="text-xs text-success">{item.restored ? "Added earlier" : "Uploaded"}</p>;
}

// Picks files from the camera or gallery and uploads each one with its own progress, retry, and remove controls.
// Capture is left unset so the phone offers both the camera and the gallery.
export function FileUploader({ upload, label, hint }: FileUploaderProps) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const full = upload.items.length >= upload.maxCount;
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <label htmlFor={inputId} className="text-sm font-medium text-zinc-700">
          {label}
        </label>
        <span className="text-xs text-muted">
          {upload.items.length} of {upload.maxCount}
        </span>
      </div>
      {hint ? <p className="-mt-2 text-xs text-muted">{hint}</p> : null}
      <input
        ref={inputRef}
        id={inputId}
        type="file"
        multiple={upload.maxCount > 1}
        accept={ATTACHMENT_LIMITS[upload.kind].accept}
        disabled={full}
        className="sr-only"
        onChange={(event) => {
          if (event.target.files) upload.add(event.target.files);
          event.target.value = "";
        }}
      />
      <Button variant="outline" className="min-h-11 w-full sm:w-auto sm:self-start" disabled={full} onClick={() => inputRef.current?.click()}>
        {full ? "File limit reached" : upload.maxCount > 1 ? "Add photos, videos, or PDFs" : "Add a receipt"}
      </Button>
      {upload.rejections.length > 0 ? (
        <ul role="alert" className="flex flex-col gap-1 text-xs text-danger">
          {upload.rejections.map((message) => (
            <li key={message}>{message}</li>
          ))}
        </ul>
      ) : null}
      {upload.items.length > 0 ? (
        <ul aria-label={`${label} files`} className="flex flex-col divide-y divide-border rounded-xl border border-border bg-card">
          {upload.items.map((item) => (
            <li key={item.localId} className="flex items-center gap-3 p-3">
              {item.previewUrl ? (
                <img src={item.previewUrl} alt="" className="size-12 shrink-0 rounded-lg object-cover" />
              ) : (
                <span aria-hidden="true" className="flex size-12 shrink-0 items-center justify-center rounded-lg bg-subtle text-xs font-medium text-muted uppercase">
                  {item.fileName.split(".").pop()?.slice(0, 4) ?? "file"}
                </span>
              )}
              <div className="flex min-w-0 flex-1 flex-col gap-1">
                <p className="truncate text-sm">
                  {item.fileName} <span className="text-xs text-muted">· {formatBytes(item.sizeBytes)}</span>
                </p>
                <ItemStatus item={item} />
              </div>
              <div className="flex shrink-0 gap-1">
                {item.status === "failed" && !item.restored ? (
                  <Button variant="outline" className="min-h-11 px-3" onClick={() => upload.retry(item.localId)}>
                    Retry
                  </Button>
                ) : null}
                <Button variant="ghost" className="min-h-11 px-3" aria-label={`Remove ${item.fileName}`} onClick={() => void upload.remove(item.localId)}>
                  Remove
                </Button>
              </div>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
