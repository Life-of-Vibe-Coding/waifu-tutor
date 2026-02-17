/**
 * Shared HTML rewrite helpers for course frame (client) and school-proxy (server).
 * Ensures relative assets load from school and same-origin links go through our frame.
 */

/** Params that trigger reload/redirect loops in iframes (e.g. ntulearn sso_reload). Strip them so we fetch stable URLs. */
const RELOAD_PARAMS = new Set(["sso_reload", "reload", "redirect", "refresh"]);

export function stripReloadParams(url: string): string {
  try {
    const u = new URL(url);
    const kept = Array.from(u.searchParams.entries()).filter(([k]) => !RELOAD_PARAMS.has(k.toLowerCase()));
    u.search = "";
    if (kept.length) u.search = new URLSearchParams(kept).toString();
    return u.href;
  } catch {
    return url;
  }
}

function resolveUrl(href: string, base: string): string {
  try {
    return new URL(href, base).href;
  } catch {
    return href;
  }
}

export function isSameOrigin(target: string, pageOrigin: string): boolean {
  try {
    const t = new URL(target);
    const o = new URL(pageOrigin);
    return t.protocol === o.protocol && t.hostname === o.hostname && t.port === o.port;
  } catch {
    return false;
  }
}

export function baseUrlForPage(pageUrl: string): string {
  try {
    const u = new URL(pageUrl);
    u.hash = "";
    u.search = "";
    const path = u.pathname.replace(/\/[^/]*$/, "/") || "/";
    u.pathname = path;
    return u.href;
  } catch {
    return pageUrl;
  }
}

export function injectBaseTag(html: string, pageUrl: string): string {
  const base = baseUrlForPage(pageUrl);
  const tag = `<base href="${base.replace(/"/g, "&quot;")}">`;
  if (/<head[\s>]/i.test(html)) {
    return html.replace(/(<head[\s>])/i, `$1${tag}`);
  }
  return tag + html;
}

export function rewriteSameOriginLinks(html: string, pageUrl: string, framePath: string): string {
  return html.replace(
    /<a\s+([^>]*?)href\s*=\s*(["']?)([^"'\s>]+)\2/gi,
    (match, before, _quote, href) => {
      const absolute = resolveUrl(href, pageUrl);
      if (!isSameOrigin(absolute, pageUrl)) return match;
      const stable = stripReloadParams(absolute);
      const encoded = encodeURIComponent(stable);
      // target="_top" so the embedding iframe (not inner srcdoc) navigates; parent can then read the URL
      const top = /target\s*=/i.test(before) ? "" : ' target="_top"';
      return `<a ${before}href="${framePath}?url=${encoded}"${top}`;
    }
  );
}

/** Injected into proxy HTML so school scripts that add sso_reload trigger navigation to the clean URL instead. */
export function getReloadParamsStripperScript(): string {
  return [
    "<script>(function(){",
    "var keys=['sso_reload','reload','redirect','refresh'];",
    "function strip(u){try{var uu=new URL(u,location.origin);keys.forEach(function(k){uu.searchParams.delete(k);});return uu.href;}catch(e){return u;}}",
    "var R=location.replace.bind(location),A=location.assign.bind(location);",
    "location.replace=function(u){R(strip(u));};",
    "location.assign=function(u){A(strip(u));};",
    "try{var d=Object.getOwnPropertyDescriptor(Location.prototype,'href');if(d&&d.set){var s=d.set;Object.defineProperty(location,'href',{set:function(v){s.call(location,strip(v));},get:d.get,configurable:!0});}}catch(e){}",
    "})();</script>",
  ].join("");
}

export function injectReloadParamsStripper(html: string): string {
  const script = getReloadParamsStripperScript();
  if (/<head[\s>]/i.test(html)) {
    return html.replace(/(<head[\s>])/i, `$1${script}`);
  }
  return script + html;
}

export function rewriteHtmlForFrame(html: string, pageUrl: string, framePath: string): string {
  let out = injectBaseTag(html, pageUrl);
  out = rewriteSameOriginLinks(out, pageUrl, framePath);
  out = injectReloadParamsStripper(out);
  return out;
}
