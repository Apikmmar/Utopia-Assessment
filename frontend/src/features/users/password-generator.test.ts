import { describe, expect, it } from "vitest";
import { createUserSchema } from "./schemas";
import { generatePassword } from "./password-generator";

describe("generatePassword", () => {
  it("returns at least 16 characters that pass the client password rule and differ between calls", () => {
    const first = generatePassword();
    const second = generatePassword();
    expect(first.length).toBeGreaterThanOrEqual(16);
    expect(first).not.toBe(second);
    const result = createUserSchema.safeParse({
      name: "A",
      email: "a@example.com",
      phone: "",
      age: "",
      roleCode: "manager",
      password: first,
    });
    expect(result.success).toBe(true);
  });
});
