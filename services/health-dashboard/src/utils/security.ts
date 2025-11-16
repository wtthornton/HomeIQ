const CSRF_COOKIE_NAME = 'homeiq_csrf';
const CSRF_HEADER_NAME = 'X-CSRF-Token';
const TOKEN_BYTES = 16;

const isBrowser = typeof window !== 'undefined';

const toHex = (buffer: Uint8Array): string =>
  Array.from(buffer, (byte) => byte.toString(16).padStart(2, '0')).join('');

const readCookie = (name: string): string | null => {
  if (!isBrowser) {
    return null;
  }

  const cookies = document.cookie?.split(';') ?? [];
  for (const cookie of cookies) {
    const [key, value] = cookie.trim().split('=');
    if (key === name) {
      return decodeURIComponent(value ?? '');
    }
  }
  return null;
};

const writeCookie = (name: string, value: string): void => {
  if (!isBrowser) {
    return;
  }

  const secure = window.location.protocol === 'https:';
  const attributes = [
    `${name}=${encodeURIComponent(value)}`,
    'Path=/',
    'SameSite=Strict',
    'Max-Age=604800', // 7 days
  ];

  if (secure) {
    attributes.push('Secure');
  }

  document.cookie = attributes.join('; ');
};

const generateToken = (): string => {
  if (!isBrowser || !window.crypto?.getRandomValues) {
    // Fallback: pseudo-random (only used in unsupported environments)
    return Math.random().toString(36).substring(2, 18);
  }

  const buffer = new Uint8Array(TOKEN_BYTES);
  window.crypto.getRandomValues(buffer);
  return toHex(buffer);
};

export const ensureCsrfToken = (): string => {
  let token = readCookie(CSRF_COOKIE_NAME);
  if (!token) {
    token = generateToken();
    writeCookie(CSRF_COOKIE_NAME, token);
  }
  return token;
};

export const getCsrfToken = (): string => ensureCsrfToken();

export const withCsrfHeader = (headers: HeadersInit = {}): HeadersInit => {
  const token = ensureCsrfToken();
  if (headers instanceof Headers) {
    headers.set(CSRF_HEADER_NAME, token);
    return headers;
  }

  if (Array.isArray(headers)) {
    const filtered = headers.filter(([key]) => key.toLowerCase() !== CSRF_HEADER_NAME.toLowerCase());
    filtered.push([CSRF_HEADER_NAME, token]);
    return filtered;
  }

  return {
    ...headers,
    [CSRF_HEADER_NAME]: token,
  };
};

export const CSRF_HEADER = CSRF_HEADER_NAME;
export const CSRF_COOKIE = CSRF_COOKIE_NAME;
