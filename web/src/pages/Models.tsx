import { useCallback, useEffect, useState } from "react";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardTitle } from "../components/ui/card";
import { Progress } from "../components/ui/progress";
import { api, onEvent } from "../lib/api";

export default function Models() {
  const [models, setModels] = useState<any[]>([]);
  const [downloads, setDownloads] = useState<Record<string, number>>({});
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    try {
      setModels(await api.getModels());
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }, []);

  useEffect(() => {
    refresh();
    return onEvent((msg) => {
      const name = msg.data?.model;
      if (!name) return;
      if (msg.event === "download_started") {
        setDownloads((prev) => ({ ...prev, [name]: 0 }));
      }
      if (msg.event === "download_progress") {
        setDownloads((prev) => ({
          ...prev,
          [name]: msg.data.downloaded_mb || 0,
        }));
      }
      if (msg.event === "download_finished" || msg.event === "download_error") {
        setDownloads((prev) => {
          const next = { ...prev };
          delete next[name];
          return next;
        });
        refresh();
      }
    });
  }, [refresh]);

  const download = async (name: string) => {
    setError("");
    try {
      await api.downloadModel(name);
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  };

  const activate = async (name: string) => {
    setError("");
    try {
      await api.setModel(name);
      refresh();
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  };

  const MODEL_META: Record<string, { desc: string; size: string }> = {
    sensevoice: {
      desc: "SenseVoice 整段识别，录完再识别，适合准确率优先",
      size: "约 0.9 GB",
    },
    "paraformer-streaming": {
      desc: "Paraformer 流式识别，边说边出字（需要流式模型）",
      size: "约 0.8 GB",
    },
    "ct-punc": {
      desc: "流式最终文本标点补全（ct-punc）",
      size: "约 1.1 GB",
    },
  };

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      {error && <p className="text-sm text-red-600">{error}</p>}
      <Card className="text-xs text-neutral-500">
        <p>
          模型默认下载到用户数据目录；也可以把已有的模型目录放到该目录，
          或直接在设置中选择。首次下载需要联网（ModelScope）。
        </p>
      </Card>
      {models.map((model) => {
        const meta = MODEL_META[model.name] || { desc: "", size: "" };
        const downloading = model.name in downloads;
        return (
          <Card key={model.name}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold">{model.label}</span>
                  {model.active && <Badge tone="green">当前使用</Badge>}
                  {!model.downloaded && !downloading && (
                    <Badge tone="neutral">未下载</Badge>
                  )}
                </div>
                <p className="mt-1 text-xs text-neutral-500">{meta.desc}</p>
                <p className="mt-0.5 text-xs text-neutral-400">
                  {model.model_id} · {meta.size}
                </p>
                {downloading && (
                  <div className="mt-2 max-w-xs">
                    <Progress value={50} />
                    <p className="mt-1 text-xs text-neutral-500">
                      下载中: {downloads[model.name] ?? 0} MB
                    </p>
                  </div>
                )}
              </div>
              <div className="flex shrink-0 gap-2">
                {!model.active && model.downloaded && (
                  <Button variant="outline" onClick={() => activate(model.name)}>
                    切换
                  </Button>
                )}
                {!model.downloaded && !downloading && (
                  <Button onClick={() => download(model.name)}>下载</Button>
                )}
              </div>
            </div>
          </Card>
        );
      })}
    </div>
  );
}
