import { useCallback, useEffect, useState } from "react";
import { Button } from "../components/ui/button";
import { Card, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Select } from "../components/ui/select";
import { Switch } from "../components/ui/switch";
import { api } from "../lib/api";

export default function Settings() {
  const [settings, setSettings] = useState<any>(null);
  const [hotkey, setHotkey] = useState("");
  const [chunkMs, setChunkMs] = useState("600");
  const [punc, setPunc] = useState(true);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    try {
      const data = await api.getSettings();
      setSettings(data);
      setHotkey(data.hotkey || "f8");
      setChunkMs(data.chunk_ms || "600");
      setPunc(String(data.punc).toLowerCase() !== "false");
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const save = async () => {
    setSaved(false);
    setError("");
    try {
      const result = await api.setSettings({
        hotkey,
        chunk_ms: Number(chunkMs),
        punc,
      });
      setSettings(result);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  };

  const captureHotkey = (e: React.KeyboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const parts: string[] = [];
    if (e.ctrlKey) parts.push("ctrl");
    if (e.shiftKey) parts.push("shift");
    if (e.altKey) parts.push("alt");
    if (e.metaKey) parts.push("cmd");
    const key = e.key.toLowerCase();
    if (["control", "shift", "alt", "meta"].includes(key)) return;
    const map: Record<string, string> = {
      " ": "space",
      escape: "esc",
      arrowleft: "left",
      arrowright: "right",
      arrowup: "up",
      arrowdown: "down",
      pageup: "page_up",
      pagedown: "page_down",
    };
    const mapped = map[key] || key;
    if (mapped.length !== 1 && !/^f\d{1,2}$/.test(mapped) && !map[key]) return;
    setHotkey([...parts, mapped].join("+"));
  };

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <Card>
        <CardTitle>快捷键</CardTitle>
        <p className="mb-2 text-xs text-neutral-500">
          点击输入框后按下新热键（支持组合键，如 Ctrl+Shift+F8）
        </p>
        <Input
          readOnly
          value={hotkey}
          onKeyDown={captureHotkey}
          onFocus={(e) => e.currentTarget.select()}
          className="w-56"
          placeholder="按快捷键..."
        />
      </Card>

      <Card>
        <CardTitle>识别参数</CardTitle>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm">流式 chunk 粒度</p>
              <p className="text-xs text-neutral-500">
                越大 CPU 压力越小，但出字延迟更高
              </p>
            </div>
            <Select value={chunkMs} onChange={(e) => setChunkMs(e.target.value)}>
              <option value="600">600ms</option>
              <option value="960">960ms</option>
            </Select>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm">流式结束补标点</p>
              <p className="text-xs text-neutral-500">
                使用 ct-punc 模型，未下载时保持原文
              </p>
            </div>
            <Switch checked={punc} onChange={setPunc} />
          </div>
        </div>
      </Card>

      <Card>
        <CardTitle>路径与版本</CardTitle>
        <dl className="space-y-1 text-xs text-neutral-600">
          <div className="flex justify-between gap-4">
            <dt>数据库</dt>
            <dd className="truncate">{settings?.db_path || "-"}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt>模型目录</dt>
            <dd className="truncate">{settings?.models_root || "-"}</dd>
          </div>
        </dl>
      </Card>

      <div className="flex items-center gap-3">
        <Button onClick={save}>保存设置</Button>
        {saved && <span className="text-sm text-green-600">已保存</span>}
        {error && <span className="text-sm text-red-600">{error}</span>}
      </div>
    </div>
  );
}
