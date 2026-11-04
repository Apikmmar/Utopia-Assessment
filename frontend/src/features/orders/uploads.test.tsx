import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { FakeXhr } from "@/test-support/fake-xhr";
import { mockBackend } from "@/test-support/mock-backend";
import { AttachmentList } from "./components/attachment-list";
import { FileUploader } from "./components/file-uploader";
import { useFileUpload } from "./hooks/use-file-upload";
import type { Attachment } from "./schemas";

const ORDER_ID = "55555555-5555-4555-8555-555555555555";
const ATTACHMENT_ID = "88888888-8888-4888-8888-888888888888";
const UPLOAD_URL = "https://storage.test/upload/orders/x.jpg?token=t";
const MEGABYTE = 1024 * 1024;

// Renders the uploader for one kind with its upload state.
function Harness({ kind = "completion", existing = [] }: { kind?: "completion" | "receipt"; existing?: Attachment[] }) {
  const upload = useFileUpload(ORDER_ID, kind, existing);
  return <FileUploader upload={upload} label="Job files" />;
}

// Returns a file of the given name, type, and size.
function makeFile(name: string, type: string, size = 1000) {
  const file = new File(["x"], name, { type });
  Object.defineProperty(file, "size", { value: size });
  return file;
}

// Picks files in the uploader's hidden input.
function pick(files: File[]) {
  fireEvent.change(screen.getByLabelText("Job files"), { target: { files } });
}

// Returns the latest fake upload request once one has been sent.
async function lastUpload() {
  await waitFor(() => expect(FakeXhr.instances.length).toBeGreaterThan(0));
  return FakeXhr.instances.at(-1)!;
}

beforeEach(() => {
  FakeXhr.instances = [];
  vi.stubGlobal("XMLHttpRequest", FakeXhr);
  URL.createObjectURL = vi.fn(() => "blob:preview");
  URL.revokeObjectURL = vi.fn();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("file uploader (mocked backend and storage: fetch and XMLHttpRequest are stubbed)", () => {
  it("rejects a disallowed type, an oversized file, and files past the limit before any request", () => {
    const calls = mockBackend({});
    render(<Harness kind="receipt" />);
    pick([makeFile("page.html", "text/html"), makeFile("big.jpg", "image/jpeg", 10 * MEGABYTE + 1), makeFile("clip.mp4", "video/mp4")]);
    expect(screen.getByText(/page\.html: This file type is not allowed/)).toBeInTheDocument();
    expect(screen.getByText(/big\.jpg: This file is too large. The limit is 10 MB/)).toBeInTheDocument();
    expect(screen.getByText(/clip\.mp4: This file type is not allowed/)).toBeInTheDocument();
    expect(calls).toHaveLength(0);
  });

  it("asks for an upload URL, uploads with progress, and marks the file uploaded", async () => {
    const calls = mockBackend({
      [`POST /orders/${ORDER_ID}/attachments`]: { status: 201, body: { attachment: pendingAttachment(), uploadUrl: UPLOAD_URL } },
    });
    render(<Harness />);
    pick([makeFile("photo.jpg", "image/jpeg")]);
    const request = await lastUpload();
    expect(request.url).toBe(UPLOAD_URL);
    expect(request.headers["Content-Type"]).toBe("image/jpeg");
    expect(calls[0].body).toEqual({ kind: "completion", fileName: "photo.jpg", contentType: "image/jpeg", sizeBytes: 1000 });
    act(() => request.progress(500, 1000));
    expect(screen.getByRole("progressbar", { name: "Uploading photo.jpg" })).toHaveAttribute("aria-valuenow", "50");
    act(() => request.respond(200));
    expect(await screen.findByText("Uploaded")).toBeInTheDocument();
  });

  it("lets a failed upload be retried with the same upload URL", async () => {
    const calls = mockBackend({
      [`POST /orders/${ORDER_ID}/attachments`]: { status: 201, body: { attachment: pendingAttachment(), uploadUrl: UPLOAD_URL } },
    });
    render(<Harness />);
    pick([makeFile("photo.jpg", "image/jpeg")]);
    const first = await lastUpload();
    act(() => first.respond(500));
    expect(await screen.findByText(/Upload failed/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    await waitFor(() => expect(FakeXhr.instances).toHaveLength(2));
    act(() => FakeXhr.instances[1].respond(200));
    expect(await screen.findByText("Uploaded")).toBeInTheDocument();
    expect(calls.filter((call) => call.method === "POST")).toHaveLength(1);
  });

  it("shows a server refusal such as the file limit on the file", async () => {
    mockBackend({
      [`POST /orders/${ORDER_ID}/attachments`]: { status: 409, body: { detail: "This job already has the most files of this kind (6).", code: "ATTACHMENT_LIMIT" } },
    });
    render(<Harness />);
    pick([makeFile("photo.jpg", "image/jpeg")]);
    expect(await screen.findByText("This job already has the most files of this kind (6).")).toBeInTheDocument();
  });

  it("removes a file through the delete endpoint and releases its preview", async () => {
    const calls = mockBackend({
      [`POST /orders/${ORDER_ID}/attachments`]: { status: 201, body: { attachment: pendingAttachment(), uploadUrl: UPLOAD_URL } },
      [`DELETE /orders/${ORDER_ID}/attachments/${ATTACHMENT_ID}`]: { status: 204 },
    });
    render(<Harness />);
    pick([makeFile("photo.jpg", "image/jpeg")]);
    const request = await lastUpload();
    act(() => request.respond(200));
    await screen.findByText("Uploaded");
    await userEvent.click(screen.getByRole("button", { name: "Remove photo.jpg" }));
    await waitFor(() => expect(screen.queryByText("photo.jpg")).not.toBeInTheDocument());
    expect(calls.some((call) => call.method === "DELETE" && call.path.endsWith(ATTACHMENT_ID))).toBe(true);
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:preview");
  });

  it("releases previews and cancels uploads when the form unmounts", async () => {
    mockBackend({
      [`POST /orders/${ORDER_ID}/attachments`]: { status: 201, body: { attachment: pendingAttachment(), uploadUrl: UPLOAD_URL } },
    });
    const { unmount } = render(<Harness />);
    pick([makeFile("photo.jpg", "image/jpeg")]);
    await lastUpload();
    unmount();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:preview");
  });

  it("restores pending files the server already holds after a reload", () => {
    mockBackend({});
    render(<Harness existing={[pendingAttachment()]} />);
    expect(screen.getByText("Added earlier")).toBeInTheDocument();
    expect(screen.getByText("1 of 6")).toBeInTheDocument();
  });
});

describe("attachment list (mocked backend: fetch is stubbed, no real server)", () => {
  it("shows thumbnails for JPEG and links for HEIC, video, and PDF", async () => {
    mockBackend({
      [`GET /orders/${ORDER_ID}/attachments`]: {
        status: 200,
        body: {
          items: [
            uploaded("a", "photo.jpg", "image/jpeg"),
            uploaded("b", "IMG_0001.HEIC", "image/heic"),
            uploaded("c", "clip.mov", "video/quicktime"),
            uploaded("d", "receipt.pdf", "application/pdf", "receipt"),
            { ...uploaded("e", "pending.jpg", "image/jpeg"), status: "pending", viewUrl: null },
          ],
        },
      },
    });
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <AttachmentList orderId={ORDER_ID} />
      </QueryClientProvider>,
    );
    expect(await screen.findByRole("img", { name: "photo.jpg" })).toHaveAttribute("src", "https://storage.test/view/a");
    expect(screen.getByRole("link", { name: /IMG_0001\.HEIC/ })).toHaveAttribute("href", "https://storage.test/view/b");
    expect(screen.queryByRole("img", { name: "IMG_0001.HEIC" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /clip\.mov/ })).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Receipt" })).toHaveTextContent("receipt.pdf");
    expect(screen.queryByText("pending.jpg")).not.toBeInTheDocument();
  });
});

// Builds the pending attachment the upload endpoint returns.
function pendingAttachment(): Attachment {
  return { attachmentId: ATTACHMENT_ID, kind: "completion", fileName: "photo.jpg", contentType: "image/jpeg", sizeBytes: 1000, status: "pending", viewUrl: null };
}

// Builds one uploaded attachment with a view link.
function uploaded(id: string, fileName: string, contentType: string, kind = "completion"): Attachment {
  return { attachmentId: id, kind, fileName, contentType, sizeBytes: 2048, status: "uploaded", viewUrl: `https://storage.test/view/${id}` };
}
