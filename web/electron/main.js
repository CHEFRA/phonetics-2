"use strict";

const { app, BrowserWindow, Tray, Menu, ipcMain, nativeImage } = require("electron");
const { spawn } = require("child_process");
const readline = require("readline");
const path = require("path");
const fs = require("fs");

const SMOKE_TEST = process.env.SMOKE_TEST === "1";

let mainWindow = null;
let tray = null;
let sidecar = null;
let sidecarReady = false;
let quitting = false;

let rpcSeq = 0;
const pending = new Map();

function resolveSidecar() {
  const devPython = process.env.PHONETICS_PYTHON;
  const devScript = process.env.PHONETICS_RPC_SCRIPT;
  if (devPython && devScript && fs.existsSync(devScript)) {
    return { cmd: devPython, args: [devScript], cwd: path.dirname(devScript) };
  }
  const exe = path.join(
    process.resourcesPath,
    "sidecar",
    "phonetics-sidecar.exe",
  );
  return { cmd: exe, args: [], cwd: path.dirname(exe) };
}

function sendRequest(method, params = {}) {
  return new Promise((resolve, reject) => {
    if (!sidecar || sidecar.stdin.destroyed) {
      reject(new Error("Python 子进程未运行"));
      return;
    }
    const id = ++rpcSeq;
    pending.set(id, { resolve, reject });
    sidecar.stdin.write(JSON.stringify({ id, method, params }) + "\n");
  });
}

function startSidecar() {
  const { cmd, args, cwd } = resolveSidecar();
  const env = { ...process.env };
  if (app.isPackaged) {
    env.DB_PATH = path.join(app.getPath("userData"), "phonetics.db");
    env.MODELS_ROOT = path.join(app.getPath("userData"), "models");
    env.DEVICE = env.DEVICE || "cpu";
  }
  sidecar = spawn(cmd, args, {
    cwd,
    env,
    windowsHide: true,
    stdio: ["pipe", "pipe", "pipe"],
  });

  const rl = readline.createInterface({ input: sidecar.stdout });
  rl.on("line", (line) => {
    let msg;
    try {
      msg = JSON.parse(line);
    } catch {
      return;
    }
    if (msg && msg.id != null && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.ok) {
        resolve(msg.result);
      } else {
        reject(
          new Error(
            (msg.error && msg.error.message) || "RPC 调用失败",
          ),
        );
      }
    } else if (msg && msg.event) {
      if (msg.event === "ready") {
        sidecarReady = true;
      }
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send("rpc-event", msg);
      }
    }
  });

  sidecar.stderr.on("data", (data) => {
    process.stderr.write(`[sidecar] ${data}`);
  });
  sidecar.on("error", (err) => {
    console.error("[sidecar] 启动失败:", err.message);
  });
  sidecar.on("exit", (code) => {
    console.log(`[sidecar] 退出 code=${code}`);
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send("rpc-event", {
        event: "sidecar_exit",
        data: { code },
      });
    }
  });
}

function forceKillSidecar() {
  if (!sidecar || sidecar.exitCode !== null) return;
  try {
    if (process.platform === "win32") {
      spawn("taskkill", ["/pid", String(sidecar.pid), "/T", "/F"], {
        windowsHide: true,
      });
    } else {
      sidecar.kill("SIGKILL");
    }
  } catch {
    // 忽略清理失败
  }
}

function quitApp() {
  quitting = true;
  try {
    sendRequest("quit").catch(() => {});
  } catch {
    // 子进程可能已退出
  }
  setTimeout(() => {
    forceKillSidecar();
    app.quit();
  }, 800);
}

function showWindow() {
  if (mainWindow) {
    mainWindow.show();
    mainWindow.focus();
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1080,
    height: 720,
    minWidth: 880,
    minHeight: 600,
    show: false,
    autoHideMenuBar: true,
    icon: path.join(__dirname, "icon.png"),
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  mainWindow.on("close", (event) => {
    if (!quitting) {
      event.preventDefault();
      mainWindow.hide();
    }
  });
  mainWindow.on("ready-to-show", () => {
    mainWindow.show();
  });

  const devUrl = process.env.VITE_DEV_SERVER_URL;
  if (devUrl) {
    mainWindow.loadURL(devUrl);
  } else {
    mainWindow.loadFile(path.join(__dirname, "../dist/index.html"));
  }
}

function createTray() {
  const iconPath = path.join(__dirname, "icon.png");
  const image = nativeImage.createFromPath(iconPath);
  tray = new Tray(image.resize({ width: 16, height: 16 }));
  tray.setToolTip("Phonetics-2");
  tray.setContextMenu(
    Menu.buildFromTemplate([
      { label: "打开主界面", click: showWindow },
      { type: "separator" },
      { label: "退出", click: quitApp },
    ]),
  );
  tray.on("click", showWindow);
}

ipcMain.handle("rpc", (_event, method, params) =>
  sendRequest(method, params || {}),
);

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on("second-instance", showWindow);

  app.whenReady().then(async () => {
    startSidecar();
    createWindow();
    if (!SMOKE_TEST) {
      createTray();
    }

    if (SMOKE_TEST) {
      try {
        await new Promise((resolve) => {
          const started = Date.now();
          const timer = setInterval(() => {
            if (sidecarReady) {
              clearInterval(timer);
              resolve();
            } else if (Date.now() - started > 20000) {
              clearInterval(timer);
              resolve();
            }
          }, 200);
        });
        const status = await sendRequest("get_status");
        console.log(
          `[smoke] ok state=${status.state} model=${status.model} version=${status.version}`,
        );
        app.exit(0);
      } catch (err) {
        console.error("[smoke] failed:", err.message || err);
        app.exit(1);
      }
    }
  });

  app.on("window-all-closed", () => {
    // 托盘应用：关闭窗口不退出
  });
  app.on("before-quit", () => {
    quitting = true;
    try {
      sendRequest("quit").catch(() => {});
    } catch {
      // 子进程可能已退出
    }
  });
  app.on("will-quit", forceKillSidecar);
}
