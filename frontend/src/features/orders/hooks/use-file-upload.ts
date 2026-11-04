import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "@/lib/api-client";
import { deleteAttachment, requestUpload, uploadFile } from "../api";
import { ATTACHMENT_LIMITS, fileContentType, fileProblem, isPreviewable, type AttachmentKind } from "../attachments";
import type { Attachment } from "../schemas";

export type UploadStatus = "uploading" | "done" | "failed";

export type UploadItem = {
  localId: string;
  fileName: string;
  contentType: string;
  sizeBytes: number;
  status: UploadStatus;
  progress: number;
  attachmentId: string | null;
  previewUrl: string | null;
  error: string | null;
  restored: boolean;
};

type Ticket = { attachmentId: string; uploadUrl: string };

const UPLOAD_FAILED_MESSAGE = "Upload failed. Check your connection and retry.";
const REMOVE_FAILED_MESSAGE = "We could not remove this file. Try again.";

// Returns the message to show for a failed upload step; server refusals keep their own wording.
function failureText(error: unknown) {
  if (error instanceof ApiError && error.status >= 400 && error.status < 500) return error.message;
  return UPLOAD_FAILED_MESSAGE;
}

// Turns a pending file the server already holds, for example after a page reload, into an item the form can submit or remove.
function restoredItem(attachment: Attachment): UploadItem {
  return {
    localId: attachment.attachmentId,
    fileName: attachment.fileName,
    contentType: attachment.contentType,
    sizeBytes: attachment.sizeBytes,
    status: "done",
    progress: 1,
    attachmentId: attachment.attachmentId,
    previewUrl: null,
    error: null,
    restored: true,
  };
}

// Uploads files of one kind for a job: client checks first, then per file a signed upload URL from the API and a direct
// PUT with progress. Failed files can be retried with the same URL or removed, and image previews are released on
// remove and unmount. Uploads are never retried automatically.
export function useFileUpload(orderId: string, kind: AttachmentKind, existing: Attachment[] = []) {
  const [items, setItems] = useState<UploadItem[]>(() => existing.filter((item) => item.kind === kind && item.status === "pending").map(restoredItem));
  const [rejections, setRejections] = useState<string[]>([]);
  const files = useRef(new Map<string, File>());
  const tickets = useRef(new Map<string, Ticket>());
  const controllers = useRef(new Map<string, AbortController>());
  const previews = useRef(new Map<string, string>());
  const counter = useRef(0);
  const maxCount = ATTACHMENT_LIMITS[kind].maxCount;

  const update = useCallback((localId: string, changes: Partial<UploadItem>) => {
    setItems((current) => current.map((item) => (item.localId === localId ? { ...item, ...changes } : item)));
  }, []);

  const start = useCallback(
    async (localId: string) => {
      const file = files.current.get(localId);
      if (!file) return;
      const contentType = fileContentType(file);
      const controller = new AbortController();
      controllers.current.set(localId, controller);
      update(localId, { status: "uploading", progress: 0, error: null });
      try {
        let ticket = tickets.current.get(localId);
        if (!ticket) {
          const response = await requestUpload(orderId, { kind, fileName: file.name, contentType, sizeBytes: file.size });
          ticket = { attachmentId: response.attachment.attachmentId, uploadUrl: response.uploadUrl };
          tickets.current.set(localId, ticket);
          update(localId, { attachmentId: ticket.attachmentId });
        }
        await uploadFile(ticket.uploadUrl, file, contentType, (progress) => update(localId, { progress }), controller.signal);
        update(localId, { status: "done", progress: 1 });
      } catch (error) {
        if (controller.signal.aborted) return;
        update(localId, { status: "failed", error: failureText(error) });
      } finally {
        controllers.current.delete(localId);
      }
    },
    [kind, orderId, update],
  );

  const add = useCallback(
    (selected: FileList | File[]) => {
      const problems: string[] = [];
      const accepted: UploadItem[] = [];
      let room = maxCount - items.length;
      for (const file of Array.from(selected)) {
        const problem = fileProblem(kind, file);
        if (problem) {
          problems.push(`${file.name}: ${problem}`);
          continue;
        }
        if (room <= 0) {
          problems.push(`${file.name}: You can attach at most ${maxCount} ${maxCount === 1 ? "file" : "files"}.`);
          continue;
        }
        room -= 1;
        counter.current += 1;
        const localId = `local-${counter.current}`;
        const contentType = fileContentType(file);
        const previewUrl = isPreviewable(contentType) ? URL.createObjectURL(file) : null;
        if (previewUrl) previews.current.set(localId, previewUrl);
        files.current.set(localId, file);
        accepted.push({
          localId, fileName: file.name, contentType, sizeBytes: file.size, status: "uploading", progress: 0,
          attachmentId: null, previewUrl, error: null, restored: false,
        });
      }
      setRejections(problems);
      if (accepted.length === 0) return;
      setItems((current) => [...current, ...accepted]);
      accepted.forEach((item) => void start(item.localId));
    },
    [items.length, kind, maxCount, start],
  );

  const retry = useCallback((localId: string) => void start(localId), [start]);

  const remove = useCallback(
    async (localId: string) => {
      const item = items.find((candidate) => candidate.localId === localId);
      if (!item) return;
      controllers.current.get(localId)?.abort();
      const attachmentId = item.attachmentId ?? tickets.current.get(localId)?.attachmentId;
      if (attachmentId) {
        try {
          await deleteAttachment(orderId, attachmentId);
        } catch (error) {
          if (!(error instanceof ApiError && error.code === "ATTACHMENT_NOT_FOUND")) {
            update(localId, { status: "failed", error: REMOVE_FAILED_MESSAGE });
            return;
          }
        }
      }
      const preview = previews.current.get(localId);
      if (preview) URL.revokeObjectURL(preview);
      previews.current.delete(localId);
      files.current.delete(localId);
      tickets.current.delete(localId);
      setItems((current) => current.filter((candidate) => candidate.localId !== localId));
    },
    [items, orderId, update],
  );

  useEffect(() => {
    const ownedPreviews = previews.current;
    const ownedControllers = controllers.current;
    return () => {
      ownedControllers.forEach((controller) => controller.abort());
      ownedPreviews.forEach((url) => URL.revokeObjectURL(url));
      ownedPreviews.clear();
    };
  }, []);

  return {
    kind,
    maxCount,
    items,
    rejections,
    add,
    retry,
    remove,
    isUploading: items.some((item) => item.status === "uploading"),
    hasFailed: items.some((item) => item.status === "failed"),
    doneIds: items.filter((item) => item.status === "done" && item.attachmentId).map((item) => item.attachmentId as string),
  };
}

export type FileUploadState = ReturnType<typeof useFileUpload>;
