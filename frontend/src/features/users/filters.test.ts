import { describe, expect, it } from "vitest";
import { readUserFilters, toUserFilterParams } from "./filters";

describe("users list URL filters", () => {
  it("reads every filter from the search params", () => {
    const filters = readUserFilters(new URLSearchParams("search=tom&roleCode=technician&page=3&pageSize=50"));
    expect(filters).toEqual({ search: "tom", roleCode: "technician", page: 3, pageSize: 50 });
  });

  it("falls back to defaults for missing or invalid values", () => {
    const filters = readUserFilters(new URLSearchParams("roleCode=pirate&page=-2&pageSize=7"));
    expect(filters).toEqual({ search: "", roleCode: "", page: 1, pageSize: 20 });
    expect(readUserFilters(new URLSearchParams("page=abc&pageSize=1e2")).page).toBe(1);
  });

  it("writes only the values that differ from their defaults", () => {
    expect(toUserFilterParams({ search: "", roleCode: "", page: 1, pageSize: 20 }).toString()).toBe("");
    expect(toUserFilterParams({ search: "a b", roleCode: "manager", page: 2, pageSize: 100 }).toString()).toBe(
      "search=a+b&roleCode=manager&page=2&pageSize=100",
    );
  });
});
