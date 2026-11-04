export const MAX_AMOUNT_CENTS = 9_999_999_999;

const AMOUNT_PATTERN = /^(\d+)(?:\.(\d{1,2}))?$/;
const CENTS_PER_RINGGIT = 100;
const myrFormatter = new Intl.NumberFormat("en-MY", { style: "currency", currency: "MYR", minimumFractionDigits: 2 });

// Converts an amount string such as "150.5" to integer cents, or null when it is not a valid amount.
export function toCents(value: string): number | null {
  const match = AMOUNT_PATTERN.exec(value.trim());
  if (!match) return null;
  const cents = Number(match[1]) * CENTS_PER_RINGGIT + Number((match[2] ?? "").padEnd(2, "0"));
  return cents <= MAX_AMOUNT_CENTS ? cents : null;
}

// Converts integer cents back to the two-decimal string the API uses.
export function fromCents(cents: number) {
  const whole = Math.floor(cents / CENTS_PER_RINGGIT);
  const fraction = String(cents % CENTS_PER_RINGGIT).padStart(2, "0");
  return `${whole}.${fraction}`;
}

// Formats an API amount string as Malaysian ringgit for display, or a dash when it is not a valid amount.
export function formatMyr(value: string | null | undefined) {
  const cents = value == null ? null : toCents(value);
  return cents === null ? "—" : myrFormatter.format(cents / CENTS_PER_RINGGIT);
}

// Previews the final amount as quoted price plus extra charges, treating blank extras as zero; the server total is authoritative.
export function finalAmountPreview(quotedPrice: string, extraCharges: string): string | null {
  const quoted = toCents(quotedPrice);
  const extra = extraCharges.trim() === "" ? 0 : toCents(extraCharges);
  if (quoted === null || extra === null || quoted + extra > MAX_AMOUNT_CENTS) return null;
  return fromCents(quoted + extra);
}
