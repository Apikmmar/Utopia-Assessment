export const MEGABYTE = 1024 * 1024;

export const ATTACHMENT_KINDS = ["completion", "receipt"] as const;
export type AttachmentKind = (typeof ATTACHMENT_KINDS)[number];

const IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp", "image/heic"] as const;
const VIDEO_TYPES = ["video/mp4", "video/quicktime"] as const;
const DOCUMENT_TYPES = ["application/pdf"] as const;

export const IMAGE_MAX_BYTES = 10 * MEGABYTE;
export const VIDEO_MAX_BYTES = 49 * MEGABYTE;

export const ATTACHMENT_LIMITS: Record<AttachmentKind, { maxCount: number; types: readonly string[]; accept: string }> = {
  completion: { maxCount: 6, types: [...IMAGE_TYPES, ...VIDEO_TYPES, ...DOCUMENT_TYPES], accept: "image/*,video/mp4,video/quicktime,application/pdf" },
  receipt: { maxCount: 1, types: [...IMAGE_TYPES, ...DOCUMENT_TYPES], accept: "image/*,application/pdf" },
};

const TYPE_BY_EXTENSION: Record<string, string> = {
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  png: "image/png",
  webp: "image/webp",
  heic: "image/heic",
  mp4: "video/mp4",
  mov: "video/quicktime",
  pdf: "application/pdf",
};
const PREVIEWABLE_TYPES = ["image/jpeg", "image/png", "image/webp"];

// Returns a file's content type, falling back to its extension when the browser leaves it blank, as some do for HEIC.
export function fileContentType(file: { name: string; type: string }) {
  if (file.type) return file.type === "image/jpg" ? "image/jpeg" : file.type;
  const extension = file.name.split(".").pop()?.toLowerCase() ?? "";
  return TYPE_BY_EXTENSION[extension] ?? "";
}

// Returns the size limit in bytes for a content type: 49 MB for video, 10 MB for everything else.
export function maxBytesFor(contentType: string) {
  return (VIDEO_TYPES as readonly string[]).includes(contentType) ? VIDEO_MAX_BYTES : IMAGE_MAX_BYTES;
}

// Returns why a file cannot be attached as this kind, or null; the server repeats every check and is authoritative.
export function fileProblem(kind: AttachmentKind, file: { name: string; type: string; size: number }) {
  const contentType = fileContentType(file);
  if (!ATTACHMENT_LIMITS[kind].types.includes(contentType)) return "This file type is not allowed. Use a photo, a short video, or a PDF.";
  if (file.size < 1) return "This file is empty.";
  const limit = maxBytesFor(contentType);
  if (file.size > limit) return `This file is too large. The limit is ${limit / MEGABYTE} MB for this type.`;
  return null;
}

// Returns whether the browser can show a thumbnail for a content type; HEIC, video, and PDF show as links instead.
export function isPreviewable(contentType: string) {
  return PREVIEWABLE_TYPES.includes(contentType);
}

// Formats a byte count as KB or MB for display.
export function formatBytes(bytes: number) {
  return bytes >= MEGABYTE ? `${(bytes / MEGABYTE).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}
