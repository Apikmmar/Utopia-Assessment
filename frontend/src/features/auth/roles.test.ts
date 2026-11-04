import { describe, expect, it } from "vitest";
import { navigationFor } from "./navigation";
import { roleLabel } from "./roles";

describe("role registry", () => {
  it("labels every known role code", () => {
    expect(roleLabel("admin")).toBe("Admin");
    expect(roleLabel("technician")).toBe("Technician");
    expect(roleLabel("manager")).toBe("Manager");
  });

  it("falls back to a readable label for a code the client does not know", () => {
    expect(roleLabel("auditor")).toBe("Unknown role (auditor)");
    expect(roleLabel("")).toBe("Unknown role");
  });

  it("gives an unknown role only the home navigation entry", () => {
    expect(navigationFor("auditor")).toEqual([{ to: "/", label: "Home" }]);
  });
});
