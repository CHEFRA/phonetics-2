export const STATUS_LABELS: Record<string, string> = {
  idle: "空闲",
  loading: "加载中",
  recording: "录音中",
  streaming: "流式监听中",
  processing: "处理中",
};

export const STATUS_COLORS: Record<string, string> = {
  idle: "bg-green-500",
  loading: "bg-blue-500",
  recording: "bg-red-500",
  streaming: "bg-red-500",
  processing: "bg-amber-500",
};

export const RESULT_STATUS_LABELS: Record<string, string> = {
  success: "成功",
  empty: "空录音",
  error: "出错",
};

export function formatMs(ms?: number | null): string {
  if (ms == null) return "-";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

export function formatMb(mb?: number | null): string {
  if (mb == null) return "-";
  if (mb >= 1024) return `${(mb / 1024).toFixed(2)} GB`;
  return `${Math.round(mb)} MB`;
}

export function formatRtf(rtf?: number | null): string {
  return rtf == null ? "-" : rtf.toFixed(3);
}

export function formatDateTime(value?: string | null): string {
  return value || "-";
}
