

## API 对接方式

```
POST http://localhost:8000/api/v1/asr
Content-Type: multipart/form-data

字段名：file（上传 wav 文件）
返回：{"text": "识别结果"}
```

---

## 完整流程方案

```
启动 asr_client.py，终端打印"监听中，按 Ctrl+Shift+Space 开始录音"

第一次按 Ctrl+Shift+Space
  → 打印"🔴 录音中..."
  → sounddevice 开始采集麦克风音频

第二次按 Ctrl+Shift+Space
  → 打印"⏹ 停止录音，识别中..."
  → 把音频帧合并，用 scipy 写成临时 wav 文件
  → POST /api/v1/asr，字段名 file 上传 wav
  → 拿到 response["text"]
  → 把原剪贴板内容暂存
  → 把识别文本写入剪贴板
  → pynput 模拟 Cmd+V（macOS）或 Ctrl+V（Windows）
  → 恢复原剪贴板内容
  → 打印"✅ {识别结果}"
  → 删除临时 wav 文件
```

---

## 依赖清单

```
pynput        # 全局快捷键监听 + 模拟粘贴按键
sounddevice   # 麦克风录音
scipy         # 写 wav 文件
numpy         # 音频帧合并
requests      # 调用 ASR API
pyperclip     # 剪贴板读写
```