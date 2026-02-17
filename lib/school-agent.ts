import { chromium, type Browser, type BrowserContext, type Page } from "playwright";
import fs from "fs";
import path from "path";

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
const CDP_URL = process.env.CHROME_CDP_URL || "http://127.0.0.1:9222";
const RECORDINGS_DIR = process.env.RECORDINGS_DIR || path.join(process.cwd(), "data", "recordings");

function getChromeDefaultUserDataDir(): string {
  if (process.env.CHROME_USER_DATA_DIR) {
    return process.env.CHROME_USER_DATA_DIR;
  }
  const home = process.env.HOME || process.env.USERPROFILE || "";
  if (process.platform === "darwin") {
    return path.join(home, "Library", "Application Support", "Google", "Chrome");
  }
  if (process.platform === "win32") {
    return path.join(process.env.LOCALAPPDATA || home, "Google", "Chrome", "User Data");
  }
  return path.join(home, ".config", "google-chrome");
}

/** Profile folder name inside user data dir (e.g. "Default", "Profile 1"). Set CHROME_PROFILE_DIRECTORY in .env and restart dev server. */
function getChromeProfileDirectory(): string {
  const raw = process.env.CHROME_PROFILE_DIRECTORY ?? "";
  const trimmed = raw.trim();
  return trimmed || "Default";
}

/** Dedicated persistent profile for Record when your main Chrome is already running. Persists login state across sessions. */
function getRecordProfileDir(): string {
  if (process.env.CHROME_RECORD_PROFILE_DIR) {
    return process.env.CHROME_RECORD_PROFILE_DIR;
  }
  return path.join(process.cwd(), "data", "chrome-record-profile");
}

export type RecordedAction =
  | { type: "goto"; url: string }
  | { type: "click"; selector: string }
  | { type: "fill"; selector: string; value: string }
  | { type: "wait"; seconds: number };

export interface FetchCourseInput {
  url: string;
  mode: "record" | "replay";
}

function urlToKey(url: string): string {
  try {
    const u = new URL(url);
    return `${u.hostname}${u.pathname}`.replace(/[^a-zA-Z0-9.-]/g, "_").slice(0, 120);
  } catch {
    return url.replace(/[^a-zA-Z0-9.-]/g, "_").slice(0, 120);
  }
}

function getRecordingPath(url: string): string {
  if (!fs.existsSync(RECORDINGS_DIR)) fs.mkdirSync(RECORDINGS_DIR, { recursive: true });
  return path.join(RECORDINGS_DIR, `${urlToKey(url)}.json`);
}

export function hasRecording(url: string): boolean {
  return fs.existsSync(getRecordingPath(url));
}

export function loadRecording(url: string): RecordedAction[] | null {
  const p = getRecordingPath(url);
  if (!fs.existsSync(p)) return null;
  try {
    const data = JSON.parse(fs.readFileSync(p, "utf8")) as { url: string; actions: RecordedAction[] };
    return data?.actions ?? null;
  } catch {
    return null;
  }
}

export function saveRecording(url: string, actions: RecordedAction[]): void {
  const p = getRecordingPath(url);
  fs.writeFileSync(p, JSON.stringify({ url, actions, createdAt: new Date().toISOString() }, null, 2), "utf8");
}

type BrowserOrContext = Browser | BrowserContext;

async function getBrowser(options?: { headless?: boolean }): Promise<BrowserOrContext> {
  try {
    return await chromium.connectOverCDP(CDP_URL, { timeout: 8000 });
  } catch {
    const userDataDir = getChromeDefaultUserDataDir();
    const profileDir = getChromeProfileDirectory();
    // #region agent log
    fetch("http://127.0.0.1:7247/ingest/e74e64de-c421-49b4-a147-afaab464f989", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        location: "lib/school-agent.ts:getBrowser:beforeLaunchPersistent",
        message: "using persistent context (your profile)",
        data: { userDataDir, profileDir, envProfile: process.env.CHROME_PROFILE_DIRECTORY ?? null },
        timestamp: Date.now(),
        hypothesisId: "B",
      }),
    }).catch(() => {});
    // #endregion
    try {
      return await chromium.launchPersistentContext(userDataDir, {
        channel: "chrome",
        headless: options?.headless ?? false,
        args: [
          `--profile-directory=${profileDir}`,
          "--disable-features=DevToolsDebuggingRestrictions",
        ],
      });
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      const profileInUse = /already in use|in use|cannot lock|profile/i.test(msg);
      if (profileInUse) {
        const recordProfileDir = getRecordProfileDir();
        if (!fs.existsSync(recordProfileDir)) {
          fs.mkdirSync(recordProfileDir, { recursive: true });
        }
        const launchOpts = {
          channel: "chrome" as const,
          headless: options?.headless ?? false,
          args: ["--disable-features=DevToolsDebuggingRestrictions"],
        };
        const maxAttempts = 3;
        const retryDelayMs = 1500;
        for (let attempt = 1; attempt <= maxAttempts; attempt++) {
          try {
            return await chromium.launchPersistentContext(recordProfileDir, launchOpts);
          } catch (recordErr) {
            if (attempt < maxAttempts) {
              await sleep(retryDelayMs);
            } else {
              throw new Error(
                "Chrome is already running with your profile. Quit Chrome completely, then try again—or run ./scripts/launch-chrome-for-record.sh and use Record to attach to that window. Manual: " +
                  '(macOS) "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9222 --user-data-dir="' +
                  userDataDir +
                  '" --profile-directory=' +
                  profileDir
              );
            }
          }
        }
      }
      throw e;
    }
  }
}

async function getContext(browserOrContext: BrowserOrContext): Promise<BrowserContext> {
  if ("contexts" in browserOrContext) {
    const ctx = browserOrContext.contexts()[0];
    return ctx ?? (await browserOrContext.newContext());
  }
  return browserOrContext;
}

export async function recordFlow(url: string): Promise<RecordedAction[]> {
  const browserOrContext = await getBrowser({ headless: false });
  const actions: RecordedAction[] = [{ type: "goto", url }];
  let done = false;

  const context = await getContext(browserOrContext);
  const page = await context.newPage();
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.bringToFront().catch(() => {});
  await sleep(1500);

  await page.exposeFunction("__recordAction", (action: RecordedAction | { type: "done" }) => {
    if (action.type === "done") {
      done = true;
      return;
    }
    actions.push(action as RecordedAction);
  });

  await page.addInitScript(() => {
    const generateSelector = (el: Element): string => {
      if (el.id && /^[a-zA-Z][\w-]*$/.test(el.id)) return `#${el.id}`;
      const tag = el.tagName.toLowerCase();
      if (el.getAttribute("name") && tag === "input") return `input[name="${el.getAttribute("name")}"]`;
      if (el.getAttribute("data-testid")) return `[data-testid="${el.getAttribute("data-testid")}"]`;
      const path: string[] = [];
      let cur: Element | null = el;
      while (cur && cur !== document.body) {
        let sel = cur.tagName.toLowerCase();
        if (cur.id && /^[a-zA-Z][\w-]*$/.test(cur.id)) {
          path.unshift(`#${cur.id}`);
          break;
        }
        const parentEl: Element | null = cur.parentElement;
        if (parentEl) {
          const siblings = Array.from(parentEl.children).filter((c: Element) => c.tagName === cur!.tagName);
          if (siblings.length > 1) {
            const idx = siblings.indexOf(cur as Element) + 1;
            sel += `:nth-of-type(${idx})`;
          }
        }
        path.unshift(sel);
        cur = parentEl;
      }
      return path.join(" > ");
    };

    const record = (type: string, payload: Record<string, unknown>) => {
      (window as unknown as { __recordAction?: (a: RecordedAction) => void }).__recordAction?.({ type, ...payload } as RecordedAction);
    };

    document.addEventListener(
      "click",
      (e) => {
        const t = e.target as Element;
        if (t && t.closest && !t.closest("script, style")) {
          const selector = generateSelector(t);
          record("click", { selector });
        }
      },
      { capture: true }
    );

    document.addEventListener(
      "change",
      (e) => {
        const t = e.target as HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement;
        if (t && (t.tagName === "INPUT" || t.tagName === "SELECT" || t.tagName === "TEXTAREA")) {
          const selector = generateSelector(t);
          const value = t.value || "";
          if (value) record("fill", { selector, value });
        }
      },
      { capture: true }
    );

    document.addEventListener(
      "keydown",
      (e) => {
        if (e.ctrlKey && e.shiftKey && e.key === "D") {
          e.preventDefault();
          (window as unknown as { __recordAction?: (a: RecordedAction | { type: "done" }) => void }).__recordAction?.({ type: "done" });
        }
      },
      { capture: true }
    );
  });

  await page.reload({ waitUntil: "domcontentloaded" });
  await sleep(500);

  const maxWait = 300000;
  const start = Date.now();
  while (!done && Date.now() - start < maxWait) {
    await sleep(500);
  }

  saveRecording(url, actions);
  await browserOrContext.close().catch(() => {});
  // Give the OS time to release the profile dir lock so the next Record click can launch again.
  await sleep(800);
  return actions;
}

export async function replayFlow(url: string): Promise<string> {
  const actions = loadRecording(url);
  if (!actions || actions.length === 0) {
    throw new Error("No recording found for this URL. Use Record mode first to record your steps.");
  }

  const browserOrContext = await getBrowser({ headless: true });
  const context = await getContext(browserOrContext);
  const page = await context.newPage();

  try {
    for (const action of actions) {
      if (action.type === "goto") {
        await page.goto(action.url, { waitUntil: "domcontentloaded", timeout: 30000 });
        await sleep(1500);
        continue;
      }
      if (action.type === "click") {
        await page.locator(action.selector).first().click({ timeout: 8000 }).catch(() => {});
        await sleep(1500);
        continue;
      }
      if (action.type === "fill") {
        await page.locator(action.selector).first().fill(action.value, { timeout: 5000 }).catch(() => {});
        await sleep(300);
        continue;
      }
      if (action.type === "wait") {
        await sleep((action.seconds || 1) * 1000);
      }
    }

    return await extractMainContent(page);
  } finally {
    await browserOrContext.close().catch(() => {});
  }
}

async function extractMainContent(page: Page): Promise<string> {
  return page.evaluate(() => {
    const main =
      document.querySelector("main") ||
      document.querySelector("[role=main]") ||
      document.querySelector(".content") ||
      document.querySelector("#content") ||
      document.body;
    const text: string[] = [];
    const walk = (node: Node) => {
      if (node.nodeType === Node.TEXT_NODE) {
        const t = node.textContent?.trim();
        if (t) text.push(t);
        return;
      }
      if (node.nodeType !== Node.ELEMENT_NODE) return;
      const el = node as Element;
      if (["script", "style", "noscript"].includes(el.tagName.toLowerCase())) return;
      const tag = el.tagName.toLowerCase();
      if (["h1", "h2", "h3", "h4", "h5", "h6"].includes(tag)) {
        text.push("\n\n## " + (el.textContent?.trim() || ""));
        return;
      }
      Array.from(el.childNodes).forEach(walk);
    };
    walk(main);
    return text.join(" ").replace(/\s+/g, " ").trim();
  });
}

export type FetchResult = { ok: true; content: string } | { ok: false; recorded?: boolean; message: string };

export async function fetchCourseWithAgent(input: FetchCourseInput): Promise<FetchResult> {
  if (input.mode === "record") {
    const actions = await recordFlow(input.url);
    return { ok: false, recorded: true, message: `Recording saved (${actions.length} actions). Use Replay next time.` };
  }
  const content = await replayFlow(input.url);
  return { ok: true, content };
}
