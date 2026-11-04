export class FakeXhr {
  static instances: FakeXhr[] = [];
  upload: { onprogress: ((event: { lengthComputable: boolean; loaded: number; total: number }) => void) | null } = { onprogress: null };
  onload: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onabort: (() => void) | null = null;
  status = 0;
  url = "";
  headers: Record<string, string> = {};

  // Records the target URL.
  open(_method: string, url: string) {
    this.url = url;
  }

  // Records one request header.
  setRequestHeader(name: string, value: string) {
    this.headers[name] = value;
  }

  // Registers the request so a test can drive it.
  send() {
    FakeXhr.instances.push(this);
  }

  // Simulates the browser cancelling the upload.
  abort() {
    this.onabort?.();
  }

  // Reports upload progress.
  progress(loaded: number, total: number) {
    this.upload.onprogress?.({ lengthComputable: true, loaded, total });
  }

  // Finishes the upload with a status.
  respond(status: number) {
    this.status = status;
    this.onload?.();
  }
}
