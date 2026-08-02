import { useEffect, useState } from "react";
import { Badge } from "../components/ui/badge";
import { Card, CardTitle } from "../components/ui/card";
import { Progress } from "../components/ui/progress";
import { api } from "../lib/api";
import { formatMs } from "../lib/format";

export default function Stats() {
  const [stats, setStats] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .getStats()
      .then(setStats)
      .catch((e: any) => setError(e?.message || String(e)));
  }, []);

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!stats) return <p className="text-sm text-neutral-400">加载中...</p>;

  const overview = stats.overview || {};
  const daily = stats.daily || [];
  const monthly = stats.monthly || [];
  const share = stats.models_share || [];
  const latency = stats.latency_trend || [];
  const maxDaily = Math.max(1, ...daily.map((d: any) => d.cnt));
  const successRate =
    overview.total > 0
      ? (((overview.success_cnt || 0) / overview.total) * 100).toFixed(1)
      : "-";

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        {[
          ["总次数", overview.total ?? "-"],
          ["成功率", `${successRate}%`],
          ["平均推理", formatMs(overview.avg_inference_ms)],
          ["平均 RTF", overview.avg_rtf?.toFixed(3) ?? "-"],
          ["平均录音", formatMs(overview.avg_audio_ms)],
        ].map(([label, value]) => (
          <Card key={label as string}>
            <p className="text-xs text-neutral-500">{label}</p>
            <p className="mt-1 text-xl font-semibold">{value}</p>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardTitle>最近 30 天使用次数</CardTitle>
          <div className="flex h-40 items-end gap-1">
            {daily.map((d: any) => (
              <div
                key={d.day}
                title={`${d.day}: ${d.cnt} 次`}
                className="flex-1 rounded-t bg-green-500"
                style={{ height: `${Math.max(2, (d.cnt / maxDaily) * 100)}%` }}
              />
            ))}
          </div>
          <div className="mt-1 flex justify-between text-[10px] text-neutral-400">
            <span>{daily[0]?.day}</span>
            <span>{daily[daily.length - 1]?.day}</span>
          </div>
        </Card>

        <Card>
          <CardTitle>模型占比</CardTitle>
          {share.length === 0 && (
            <p className="text-sm text-neutral-400">暂无数据</p>
          )}
          <div className="space-y-3">
            {share.map((s: any) => (
              <div key={s.model}>
                <div className="mb-1 flex justify-between text-xs">
                  <span>{s.model}</span>
                  <span className="text-neutral-500">
                    {s.cnt} 次 · {s.pct}%
                  </span>
                </div>
                <Progress value={s.pct} />
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card>
        <CardTitle>最近 30 天延迟趋势（成功记录）</CardTitle>
        {latency.length === 0 && (
          <p className="text-sm text-neutral-400">暂无数据</p>
        )}
        <div className="space-y-1">
          {latency
            .slice()
            .reverse()
            .map((d: any) => (
              <div
                key={d.day}
                className="flex items-center gap-3 text-xs text-neutral-600"
              >
                <span className="w-24 shrink-0">{d.day}</span>
                <span className="w-40 shrink-0">
                  推理 {formatMs(d.avg_inference_ms)}
                </span>
                <Badge tone="neutral">RTF {d.avg_rtf?.toFixed(3) ?? "-"}</Badge>
                <span className="text-neutral-400">{d.cnt} 次</span>
              </div>
            ))}
        </div>
      </Card>

      <Card>
        <CardTitle>每月使用次数</CardTitle>
        <div className="flex flex-wrap gap-2">
          {monthly.map((m: any) => (
            <Badge key={m.month} tone="green">
              {m.month}: {m.cnt} 次
            </Badge>
          ))}
          {monthly.length === 0 && (
            <p className="text-sm text-neutral-400">暂无数据</p>
          )}
        </div>
      </Card>
    </div>
  );
}
