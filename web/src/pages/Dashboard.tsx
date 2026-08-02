import { useCallback, useEffect, useState } from "react";
import { api, onEvent } from "../lib/api";
import { formatMb, STATUS_COLORS, STATUS_LABELS } from "../lib/format";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardTitle } from "../components/ui/card";

interface Status {
  state: string;
  model: string;
  mode: string;
  hotkey: string;
  memory_mb: number;
  version: string;
  models_root: string;
  db_path: string;
}

export default function Dashboard() {
  const [status, setStatus] = useState<Status | null>(null);
  const [lastResult, setLastResult] = useState<any>(null);
  const [partial, setPartial] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setStatus(await api.getStatus());
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }, []);

  useEffect(() => {
    refresh();
    return onEvent((msg) => {
      if (msg.event === "state" && msg.data) {
        setStatus((prev) => ({ ...(prev as Status), state: msg.data.state }));
      }
      if (msg.event === "result" && msg.data) {
        setLastResult(msg.data);
        setPartial("");
      }
      if (msg.event === "partial" && msg.data) {
        setPartial(msg.data.text || "");
      }
      if (msg.event === "recording_started") {
        setLastResult(null);
      }
    });
  }, [refresh]);

  const act = async (fn: () => Promise<any>) => {
    setBusy(true);
    setError("");
    try {
      setStatus(await fn());
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  };

  const state = status?.state || "idle";
  const recording = state === "recording" || state === "streaming";
  const resultText = partial || lastResult?.text || "";

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <Card>
        <div className="flex items-center gap-4">
          <span
            className={`h-12 w-12 rounded-full ${STATUS_COLORS[state] || STATUS_COLORS.idle}`}
          />
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="text-lg font-semibold">
                {STATUS_LABELS[state] || state}
              </span>
              {status?.mode === "stream" && <Badge tone="blue">流式</Badge>}
            </div>
            <p className="mt-0.5 text-sm text-neutral-500">
              当前模型: {status?.model || "-"} | 热键: {status?.hotkey || "-"} |
              内存: {status ? formatMb(status.memory_mb) : "-"}
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              disabled={busy || (state !== "idle" && !recording)}
              onClick={() => act(api.toggleRecord)}
            >
              {recording ? "停止" : "开始录音"}
            </Button>
            {recording && (
              <Button variant="danger" onClick={() => act(api.cancelRecord)}>
                取消
              </Button>
            )}
          </div>
        </div>
      </Card>

      <Card>
        <CardTitle>最近识别结果</CardTitle>
        {error && <p className="mb-2 text-sm text-red-600">{error}</p>}
        {resultText ? (
          <p className="whitespace-pre-wrap text-sm leading-6">{resultText}</p>
        ) : (
          <p className="text-sm text-neutral-400">
            {partial ? "正在输入..." : "暂无结果，按 F8 或点击开始录音"}
          </p>
        )}
        {lastResult && !partial && (
          <div className="mt-3 flex flex-wrap gap-3 text-xs text-neutral-500">
            <span>状态: {lastResult.status}</span>
            <span>时长: {(lastResult.audio_duration_ms / 1000).toFixed(1)}s</span>
            {lastResult.inference_ms != null && (
              <span>推理: {(lastResult.inference_ms / 1000).toFixed(2)}s</span>
            )}
            {lastResult.rtf != null && <span>RTF: {lastResult.rtf}</span>}
          </div>
        )}
      </Card>

      <Card className="text-xs text-neutral-500">
        <p>使用方式：全局热键 {status?.hotkey || "F8"} 开始/停止，Esc 取消。</p>
        <p className="mt-1">
          识别结果会自动粘贴到当前焦点窗口；本窗口用于查看状态、历史与设置。
        </p>
        <p className="mt-1">
          版本 {status?.version || "-"} | 模型目录: {status?.models_root || "-"}
        </p>
      </Card>
    </div>
  );
}
