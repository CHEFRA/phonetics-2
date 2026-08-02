"use strict";

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("desktop", {
  rpc: (method, params) => ipcRenderer.invoke("rpc", method, params),
  onEvent: (callback) => {
    ipcRenderer.on("rpc-event", (_event, msg) => callback(msg));
  },
});
