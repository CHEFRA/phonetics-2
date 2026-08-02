import { useCallback, useEffect, useState } from "react";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Select } from "../components/ui/select";
import { Table, TBody, TD, TH, THead, TR } from "../components/ui/table";
import { api } from "../lib/api";
import {
  formatDateTime,
  formatMb,
  formatMs,
  formatRtf,
  RESULT_STATUS_LABELS,
} from "../lib/format";

const STATUS_TONES: Record<string, "green" | "amber" | "red"> = {
  success: "green",
  empty: "amber",
  error: "red",
};

const PAGE_SIZE = 20;

export default function History() {
  const [rows, setRows] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [model, setModel] = useState("");
  const [models, setModels] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(
    async (nextOffset = 0) => {
      setLoading(true);
      setError("");
      try {
        const params: Record<string, unknown> = {
          limit: PAGE_SIZE,
          offset: nextOffset,
        };
        if (query) params.query = query;
        if (status) params.status = status;
        if (model) params.model = model;
        const result = await api.getHistory(params);
        setRows(result[0] || []);
        setTotal(result[1] || 0);
        setOffset(nextOffset);
        const unique = new Set<string>();
        (result[0] || []).forEach((row: any) => unique.add(row.model));
        setModels(Array.from(unique));
      } catch (e: any) {
        setError(e?.message || String(e));
      } finally {
        setLoading(false);
      }
    },
    [query, status, model],
  );

  useEffect(() => {
    load(0);
  }, [load]);

  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const page = Math.floor(offset / PAGE_SIZE) + 1;

  return (
    <div className="mx-auto max-w-5xl space-y-3">
      <Card>
        <CardTitle>识别历史</CardTitle>
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <Input
            placeholder="搜索文本..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-48"
          />
          <Select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">全部状态</option>
            <option value="success">成功</option>
            <option value="empty">空录音</option>
            <option value="error">出错</option>
          </Select>
          <Select value={model} onChange={(e) => setModel(e.target.value)}>
            <option value="">全部模型</option>
            {models.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </Select>
          <Button variant="outline" onClick={() => load(0)} disabled={loading}>
            查询
          </Button>
          <span className="ml-auto text-xs text-neutral-500">
            共 {total} 条
          </span>
        </div>
        {error && <p className="mb-2 text-sm text-red-600">{error}</p>}
        <Table>
          <THead>
            <TR>
              <TH>时间</TH>
              <TH>模型</TH>
              <TH>模式</TH>
              <TH>状态</TH>
              <TH>文本</TH>
              <TH>录音</TH>
              <TH>推理</TH>
              <TH>RTF</TH>
              <TH>内存</TH>
            </TR>
          </THead>
          <TBody>
            {rows.map((row) => (
              <TR key={row.id}>
                <TD className="whitespace-nowrap text-xs">
                  {formatDateTime(row.created_at)}
                </TD>
                <TD className="whitespace-nowrap text-xs">{row.model}</TD>
                <TD className="text-xs">
                  {row.mode === "stream" ? "流式" : "整段"}
                </TD>
                <TD>
                  <Badge tone={STATUS_TONES[row.status] || "neutral"}>
                    {RESULT_STATUS_LABELS[row.status] || row.status}
                  </Badge>
                </TD>
                <TD className="max-w-xs truncate">{row.text || "-"}</TD>
                <TD className="whitespace-nowrap text-xs">
                  {formatMs(row.audio_duration_ms)}
                </TD>
                <TD className="whitespace-nowrap text-xs">
                  {formatMs(row.inference_ms)}
                </TD>
                <TD className="text-xs">{formatRtf(row.rtf)}</TD>
                <TD className="whitespace-nowrap text-xs">
                  {row.mem_after_mb != null ? formatMb(row.mem_after_mb) : "-"}
                </TD>
              </TR>
            ))}
            {rows.length === 0 && (
              <TR>
                <TD colSpan={9} className="py-6 text-center text-neutral-400">
                  暂无记录
                </TD>
              </TR>
            )}
          </TBody>
        </Table>
        <div className="mt-3 flex items-center justify-between text-xs text-neutral-500">
          <span>
            第 {page} / {pages} 页
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              disabled={offset === 0 || loading}
              onClick={() => load(Math.max(0, offset - PAGE_SIZE))}
            >
              上一页
            </Button>
            <Button
              variant="outline"
              disabled={offset + PAGE_SIZE >= total || loading}
              onClick={() => load(offset + PAGE_SIZE)}
            >
              下一页
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
