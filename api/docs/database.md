# 数据库结构说明

数据库文件位于项目根目录 `data/phonetics.db`（可用环境变量 `DB_PATH` 覆盖）。
程序在第一次启动时自动创建数据库文件和全部表，不需要手动建表。

## sessions 会话表

桌面客户端或 API 服务每次启动登记一个会话，用于把连续的使用过程分组。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT | 会话唯一标识（UUID），主键 |
| app | TEXT | 来源：desktop（桌面客户端）/ api（API 服务） |
| version | TEXT | 应用版本 |
| device | TEXT | 运行设备信息（操作系统等） |
| model | TEXT | 本次会话使用的模型 |
| started_at | TEXT | 会话开始时间，本地时间 YYYY-MM-DD HH:MM:SS |
| ended_at | TEXT | 会话结束时间，NULL 表示会话仍在进行 |
| status | TEXT | running（运行中）/ closed（已结束） |

## transcriptions 转写记录表

每次语音识别产生一条记录，是后续使用分析的主要数据来源。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 自增主键 |
| session_id | TEXT | 所属会话 id |
| created_at | TEXT | 识别完成时间（本地时间） |
| source | TEXT | 来源：desktop / api |
| model | TEXT | 使用的模型（如 SenseVoiceSmall） |
| mode | TEXT | 识别模式：batch（整段）/ stream（流式，预留） |
| language | TEXT | 语言参数，默认 auto |
| text | TEXT | 识别文本，失败或空录音时为空字符串 |
| audio_duration_ms | INTEGER | 录音时长（毫秒） |
| inference_ms | INTEGER | 推理耗时（毫秒） |
| rtf | REAL | 实时率 = 推理耗时 / 录音时长，数值越小越快 |
| mem_before_mb | REAL | 推理前进程内存（MB） |
| mem_after_mb | REAL | 推理后进程内存（MB） |
| status | TEXT | success（成功）/ empty（录音为空）/ error（识别出错） |
| error | TEXT | 出错信息，成功时为 NULL |

## settings 设置表

预留的键值配置表，供后续设置功能（模型选择、热键等）使用。

| 字段 | 类型 | 说明 |
|------|------|------|
| key | TEXT | 配置项名称，主键 |
| value | TEXT | 配置值 |
| updated_at | TEXT | 最后更新时间 |

## 常用统计 SQL

每日使用次数：

```sql
SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS cnt
FROM transcriptions
GROUP BY day ORDER BY day;
```

平均推理耗时与实时率：

```sql
SELECT AVG(inference_ms) / 1000.0 AS avg_infer_s, AVG(rtf) AS avg_rtf
FROM transcriptions
WHERE status = 'success';
```
