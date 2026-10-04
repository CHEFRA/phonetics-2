"""macOS 权限自检与引导

终端版语音输入在 macOS 上依赖三项系统权限(TCC),授权对象是运行
本程序的终端 App(Terminal / iTerm / VS Code 等),授权一次长期生效:

- 辅助功能(Accessibility): 模拟 Cmd+V 粘贴必需
- 输入监控(Input Monitoring): 全局热键监听必需
- 麦克风(Microphone): 录音必需,首次录音时系统自动弹窗

"输入监控"没有可靠的公开检测接口,这里只检测"辅助功能",
其余两项通过引导文案说明。
"""

import ctypes
import logging

# ApplicationServices 框架提供 AXIsProcessTrusted
_APPLICATION_SERVICES = (
    "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
)

_GUIDE = """\
[权限提示] 未检测到"辅助功能"权限,以下功能将不可用:
- 按热键开始/停止录音
- 识别结果自动粘贴到焦点窗口

请打开 系统设置 → 隐私与安全性 → 辅助功能,
把运行本程序的终端 App(如 Terminal / iTerm)的开关打开,
然后重启本程序。

同时请检查:
- 隐私与安全性 → 输入监控: 全局热键需要,同样授权给终端 App
- 麦克风: 首次录音时系统会弹窗请求,允许即可
"""


def accessibility_granted() -> bool:
    """当前进程是否已获得辅助功能权限(继承自宿主终端 App)

    检测失败时返回 True,避免因检测问题阻塞启动。
    """
    try:
        lib = ctypes.CDLL(_APPLICATION_SERVICES)
        lib.AXIsProcessTrusted.restype = ctypes.c_bool
        return bool(lib.AXIsProcessTrusted())
    except Exception:
        logging.warning("AXIsProcessTrusted 检测失败,跳过权限检查", exc_info=True)
        return True


def warn_if_restricted() -> bool:
    """辅助功能未授权时打印引导文案;返回当前是否已授权

    权限缺失不阻塞启动: 程序仍会运行并显示菜单栏图标,
    但热键与自动粘贴在授权前无法工作。
    """
    if accessibility_granted():
        return True
    print(_GUIDE)
    logging.warning("辅助功能权限未授权,热键与自动粘贴将不可用")
    return False
