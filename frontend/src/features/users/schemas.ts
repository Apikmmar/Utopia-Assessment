import { z } from "zod";
import { passwordLengthField } from "@/features/auth/schemas";

export const NAME_MAX_LENGTH = 100;
export const EMAIL_MAX_LENGTH = 255;
export const AGE_MIN = 16;
export const AGE_MAX = 100;
export const PHONE_MIN_DIGITS = 8;
export const PHONE_MAX_DIGITS = 15;

export const userSchema = z.object({
  userId: z.string(),
  name: z.string(),
  email: z.string(),
  phone: z.string().nullable(),
  age: z.number().nullable(),
  roleCode: z.string(),
  createdAt: z.string(),
});

export const userListSchema = z.object({
  items: z.array(userSchema),
  total: z.number(),
  page: z.number(),
  pageSize: z.number(),
});

export type User = z.infer<typeof userSchema>;
export type UserList = z.infer<typeof userListSchema>;

const phoneMessage = `Phone must be ${PHONE_MIN_DIGITS} to ${PHONE_MAX_DIGITS} digits.`;
const ageMessage = `Age must be between ${AGE_MIN} and ${AGE_MAX}.`;

// Strips spaces, dashes, and one leading plus the way the server does.
export function normalizePhone(value: string) {
  const stripped = value.trim().replace(/[ -]/g, "");
  return stripped.startsWith("+") ? stripped.slice(1) : stripped;
}

const nameField = z.string().trim().min(1, "Enter a name.").max(NAME_MAX_LENGTH, `Name must be at most ${NAME_MAX_LENGTH} characters.`);

const phoneField = z.string().refine((value) => {
  const digits = normalizePhone(value);
  return digits === "" || (/^[0-9]+$/.test(digits) && digits.length >= PHONE_MIN_DIGITS && digits.length <= PHONE_MAX_DIGITS);
}, phoneMessage);

const ageField = z.string().refine((value) => {
  const text = value.trim();
  if (text === "") return true;
  const age = Number(text);
  return Number.isInteger(age) && age >= AGE_MIN && age <= AGE_MAX;
}, ageMessage);

const roleField = z.string().trim().min(1, "Choose a role.");

const detailsShape = { name: nameField, phone: phoneField, age: ageField, roleCode: roleField };

// Adds the technician-requires-phone rule to a form shape with phone and role fields.
function requireTechnicianPhone<T extends z.ZodType<{ phone: string; roleCode: string }>>(schema: T) {
  return schema.refine((values) => values.roleCode !== "technician" || normalizePhone(values.phone) !== "", {
    path: ["phone"],
    message: "Phone is required for a technician.",
  });
}

export const createUserSchema = requireTechnicianPhone(
  z.object({
    ...detailsShape,
    email: z.string().trim().min(1, "Enter an email.").max(EMAIL_MAX_LENGTH, "Email is too long.").email("Enter a valid email address."),
    password: passwordLengthField,
  }),
);

export const editUserSchema = requireTechnicianPhone(z.object(detailsShape));

export type CreateUserValues = z.infer<typeof createUserSchema>;
export type EditUserValues = z.infer<typeof editUserSchema>;

export type CreateUserPayload = {
  name: string;
  email: string;
  phone?: string;
  age?: number;
  roleCode: string;
  password: string;
};

export type UpdateUserPayload = {
  name?: string;
  phone?: string | null;
  age?: number | null;
  roleCode?: string;
};
