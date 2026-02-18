/** No Next.js rewrites; pass-through. */
export function stripReloadParams(url: string): string {
  return url;
}
