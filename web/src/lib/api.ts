export interface RpcEvent {
  event: string;
  data: any;
}

export interface DesktopBridge {
  rpc(method: string, params?: Record<string, unknown>): Promise<any>;
  onEvent(callback: (msg: RpcEvent) => void): void;
}

declare global {
  interface Window {
    desktop?: DesktopBridge;
  }
}

function bridge(): DesktopBridge {
  if (!window.desktop) {
    throw new Error("桌面桥未初始化，请在 Electron 窗口中运行");
  }
  return window.desktop;
}

export async function rpc<T = any>(
  method: string,
  params: Record<string, unknown> = {},
): Promise<T> {
  return bridge().rpc(method, params) as Promise<T>;
}

export const api = {
  getStatus: () => rpc("get_status"),
  toggleRecord: () => rpc("toggle_record"),
  cancelRecord: () => rpc("cancel_record"),
  getHistory: (params: Record<string, unknown> = {}) =>
    rpc("get_history", params),
  getStats: () => rpc("get_stats"),
  getSettings: () => rpc("get_settings"),
  setSettings: (values: Record<string, unknown>) =>
    rpc("set_settings", { values }),
  setModel: (model: string) => rpc("set_model", { model }),
  setHotkey: (hotkey: string) => rpc("set_hotkey", { hotkey }),
  downloadModel: (model: string) => rpc("download_model", { model }),
  getModels: () => rpc("get_models"),
};

export function onEvent(callback: (msg: RpcEvent) => void): () => void {
  if (!window.desktop) {
    return () => {};
  }
  window.desktop.onEvent(callback);
  return () => {};
}
