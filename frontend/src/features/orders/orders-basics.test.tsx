import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockBackend } from "@/test-support/mock-backend";
import { listServiceTypes } from "./api";
import { StatusBadge } from "./components/status-badge";
import { readOrderFilters, toOrderFilterParams } from "./filters";
import { finalAmountPreview, formatMyr, fromCents, toCents } from "./money";
import { statusLabel, statusTone } from "./statuses";

const TECH_ID = "33333333-3333-4333-8333-333333333333";

describe("order status registry", () => {
  it("labels and tones every known status", () => {
    expect(statusLabel("in_progress")).toBe("In progress");
    expect(statusLabel("job_done")).toBe("Job done");
    expect(statusTone("reviewed")).toBe("success");
  });

  it("falls back for a status this client does not know", () => {
    expect(statusLabel("on_hold")).toBe("Unknown status (on_hold)");
    expect(statusLabel("")).toBe("Unknown status");
    expect(statusTone("on_hold")).toBe("neutral");
  });

  it("renders a badge for known and unknown statuses", () => {
    render(
      <>
        <StatusBadge status="assigned" />
        <StatusBadge status="on_hold" />
      </>,
    );
    expect(screen.getByText("Assigned")).toBeInTheDocument();
    expect(screen.getByText("Unknown status (on_hold)")).toBeInTheDocument();
  });
});

describe("order money helpers", () => {
  it("converts amount strings to integer cents and back", () => {
    expect(toCents("150.5")).toBe(15050);
    expect(toCents("0")).toBe(0);
    expect(toCents("99999999.99")).toBe(9_999_999_999);
    expect(fromCents(17050)).toBe("170.50");
    expect(fromCents(5)).toBe("0.05");
  });

  it("refuses invalid amounts", () => {
    for (const value of ["", "-1", "1.005", "abc", "1e3", "100000000.00", "1."]) {
      expect(toCents(value)).toBeNull();
    }
  });

  it("previews the final amount without floating point error", () => {
    expect(finalAmountPreview("150.00", "20.50")).toBe("170.50");
    expect(finalAmountPreview("0.10", "0.20")).toBe("0.30");
    expect(finalAmountPreview("150.00", "")).toBe("150.00");
    expect(finalAmountPreview("150.00", "abc")).toBeNull();
    expect(finalAmountPreview("99999999.99", "0.01")).toBeNull();
  });

  it("formats ringgit for display", () => {
    expect(formatMyr("170.5")).toMatch(/RM\s?170\.50/);
    expect(formatMyr("1234567.00")).toMatch(/RM\s?1,234,567\.00/);
    expect(formatMyr(null)).toBe("—");
    expect(formatMyr("bad")).toBe("—");
  });
});

describe("order list URL filters", () => {
  it("reads every filter, including repeated statuses", () => {
    const filters = readOrderFilters(
      new URLSearchParams(`search=ORD-00&status=new&status=assigned&technicianId=${TECH_ID}&sort=oldest&page=2&pageSize=50`),
    );
    expect(filters).toEqual({ search: "ORD-00", status: ["new", "assigned"], technicianId: TECH_ID, sort: "oldest", page: 2, pageSize: 50 });
  });

  it("drops unknown and repeated values and falls back to defaults", () => {
    const filters = readOrderFilters(new URLSearchParams("status=pirate&status=new&status=new&technicianId=x&sort=random&page=0&pageSize=7"));
    expect(filters).toEqual({ search: "", status: ["new"], technicianId: "", sort: "newest", page: 1, pageSize: 20 });
  });

  it("writes only values that differ from their defaults", () => {
    const defaults = readOrderFilters(new URLSearchParams());
    expect(toOrderFilterParams(defaults).toString()).toBe("");
    expect(toOrderFilterParams({ ...defaults, status: ["job_done"], sort: "oldest" }).toString()).toBe("status=job_done&sort=oldest");
  });
});

describe("service types API (mocked backend: fetch is stubbed, no real server)", () => {
  it("returns the parsed service types", async () => {
    mockBackend({
      "GET /service-types": { status: 200, body: { items: [{ serviceTypeId: "st-1", code: "repair", name: "Repair" }] } },
    });
    await expect(listServiceTypes()).resolves.toEqual([{ serviceTypeId: "st-1", code: "repair", name: "Repair" }]);
  });

  it("rejects a response that does not match the contract", async () => {
    mockBackend({ "GET /service-types": { status: 200, body: { items: [{ serviceTypeId: 1, code: "repair" }] } } });
    await expect(listServiceTypes()).rejects.toThrow();
  });
});
