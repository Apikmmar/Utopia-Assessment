const ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789";
const DEFAULT_LENGTH = 16;

// Builds a random password from unambiguous characters using the browser's secure random source.
export function generatePassword(length = DEFAULT_LENGTH) {
  const limit = 256 - (256 % ALPHABET.length);
  const chars: string[] = [];
  while (chars.length < length) {
    const bytes = crypto.getRandomValues(new Uint8Array(length * 2));
    for (const byte of bytes) {
      if (byte < limit && chars.length < length) chars.push(ALPHABET[byte % ALPHABET.length]);
    }
  }
  return chars.join("");
}
