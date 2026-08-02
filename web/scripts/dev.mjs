import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const apiDir = path.resolve(root, "../api");
const isWin = process.platform === "win32";
const npx = isWin ? "npx.cmd" : "npx";
const python =
  process.env.PHONETICS_PYTHON ||
  path.join(apiDir, ".venv", "Scripts", "python.exe");
const rpcScript = path.join(apiDir, "desktop", "rpc_server.py");

console.log(`[dev] python=${python}`);
console.log(`[dev] rpc=${rpcScript}`);

const vite = spawn(npx, ["vite"], { cwd: root, stdio: "inherit" });
const electron = spawn(npx, ["electron", "."], {
  cwd: root,
  stdio: "inherit",
  env: {
    ...process.env,
    PHONETICS_PYTHON: python,
    PHONETICS_RPC_SCRIPT: rpcScript,
    VITE_DEV_SERVER_URL: "http://localhost:5173",
  },
});

function shutdown(code) {
  try {
    electron.kill("SIGTERM");
  } catch {
    // ignore
  }
  try {
    vite.kill("SIGTERM");
  } catch {
    // ignore
  }
  process.exit(code);
}

electron.on("exit", (code) => shutdown(code ?? 0));
vite.on("exit", (code) => {
  if (code !== 0) shutdown(code ?? 1);
});
process.on("SIGINT", () => shutdown(0));
process.on("SIGTERM", () => shutdown(0));
