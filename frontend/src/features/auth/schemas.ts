import { z } from "zod";

export const PASSWORD_MIN_LENGTH = 10;
export const PASSWORD_MAX_LENGTH = 128;

export const authUserSchema = z.object({
  userId: z.string(),
  name: z.string(),
  email: z.string(),
  roleCode: z.string(),
});

export const sessionSchema = z.object({ user: authUserSchema });

export const messageSchema = z.object({ message: z.string() });

export type AuthUser = z.infer<typeof authUserSchema>;

export const emailField = z.string().trim().min(1, "Enter your email.").email("Enter a valid email address.");

export const passwordLengthField = z
  .string()
  .min(PASSWORD_MIN_LENGTH, `Password must be at least ${PASSWORD_MIN_LENGTH} characters.`)
  .max(PASSWORD_MAX_LENGTH, `Password must be at most ${PASSWORD_MAX_LENGTH} characters.`);

export const loginSchema = z.object({
  email: emailField,
  password: z.string().min(1, "Enter your password."),
});

export const resetSchema = z.object({
  email: emailField,
  newPassword: passwordLengthField,
});

export type LoginValues = z.infer<typeof loginSchema>;
export type ResetValues = z.infer<typeof resetSchema>;

const WEAK_PASSWORD_MESSAGES: Record<string, string> = {
  too_short: `Password must be at least ${PASSWORD_MIN_LENGTH} characters.`,
  too_long: `Password must be at most ${PASSWORD_MAX_LENGTH} characters.`,
  too_common: "That password is too common. Choose a less guessable one.",
};

// Turns a server password reason code into a readable message.
export function weakPasswordMessage(reason: string | undefined) {
  return (reason && WEAK_PASSWORD_MESSAGES[reason]) || "Choose a stronger password.";
}
