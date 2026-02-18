import { spawn } from "node:child_process";
import http from "node:http";
import net from "node:net";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const frontendDir = path.resolve(__dirname, "..");
const backendDir = path.resolve(frontendDir, "../backend");
const preferredPort = 8000;
const fallbackPortStart = 8001;
const fallbackPortEnd = 8015;

function log(msg) {
  process.stdout.write(`[dev:all] ${msg}\n`);
}

function isPortFree(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.once("error", () => resolve(false));
    server.once("listening", () => {
      server.close(() => resolve(true));
    });
    server.listen(port, "127.0.0.1");
  });
}

function requestJson(url, timeoutMs = 1500) {
  return new Promise((resolve) => {
    const req = http.get(url, (res) => {
      let body = "";
      res.on("data", (chunk) => {
        body += String(chunk);
      });
      res.on("end", () => {
        try {
          resolve(JSON.parse(body));
        } catch {
          resolve(null);
        }
      });
    });

    req.setTimeout(timeoutMs, () => {
      req.destroy();
      resolve(null);
    });
    req.on("error", () => resolve(null));
  });
}

async function looksLikeWaifuBackend(port) {
  const doc = await requestJson(`http://127.0.0.1:${port}/openapi.json`);
  const hasChatPath = !!doc?.paths?.["/api/ai/chat"];
  const isWaifuTitle = doc?.info?.title === "Waifu Tutor API";
  return hasChatPath || isWaifuTitle;
}

async function pickBackendPort() {
  if (await isPortFree(preferredPort)) {
    return { port: preferredPort, reuseExisting: false };
  }

  if (await looksLikeWaifuBackend(preferredPort)) {
    return { port: preferredPort, reuseExisting: true };
  }

  for (let port = fallbackPortStart; port <= fallbackPortEnd; port += 1) {
    if (await isPortFree(port)) {
      return { port, reuseExisting: false };
    }
  }

  throw new Error(`No free port found in ${fallbackPortStart}-${fallbackPortEnd}`);
}

function runProcess(command, args, options = {}) {
  return spawn(command, args, {
    cwd: options.cwd,
    env: options.env ?? process.env,
    stdio: "inherit",
    shell: process.platform === "win32",
  });
}

async function main() {
  const { port, reuseExisting } = await pickBackendPort();
  const apiBaseUrl = `http://127.0.0.1:${port}`;
  const children = [];
  let shuttingDown = false;

  log(`Using backend base URL: ${apiBaseUrl}`);
  if (reuseExisting) {
    log(`Reusing existing Waifu backend on port ${port}.`);
  } else if (port !== preferredPort) {
    log(`Port ${preferredPort} is occupied by another service, starting backend on ${port}.`);
  }

  const shutdown = (code = 0) => {
    if (shuttingDown) return;
    shuttingDown = true;
    for (const child of children) {
      if (child && !child.killed) child.kill("SIGTERM");
    }
    process.exit(code);
  };

  process.on("SIGINT", () => shutdown(0));
  process.on("SIGTERM", () => shutdown(0));

  if (!reuseExisting) {
    const backend = runProcess(
      "uv",
      ["run", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", String(port)],
      { cwd: backendDir }
    );
    children.push(backend);
    backend.on("exit", (code, signal) => {
      if (shuttingDown) return;
      log(`Backend exited unexpectedly (code=${code ?? "null"}, signal=${signal ?? "null"}).`);
      shutdown(code ?? 1);
    });
  }

  const frontend = runProcess("npm", ["run", "dev"], {
    cwd: frontendDir,
    env: { ...process.env, VITE_API_BASE_URL: apiBaseUrl },
  });
  children.push(frontend);
  frontend.on("exit", (code, signal) => {
    if (shuttingDown) return;
    log(`Frontend exited (code=${code ?? "null"}, signal=${signal ?? "null"}).`);
    shutdown(code ?? 0);
  });
}

main().catch((error) => {
  const msg = error instanceof Error ? error.message : String(error);
  log(`Failed to start dev:all - ${msg}`);
  process.exit(1);
});
