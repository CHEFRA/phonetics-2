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

授权方法(二选一):
1. 手动: Apple 菜单 → 系统设置 → 隐私与安全性,
   往下滚动找到「辅助功能」,给运行本程序的终端 App 打开开关
2. 终端执行以下命令,直达设置页:
   open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"

列表里没有终端 App 时点 + 添加(终端.app 在 应用程序/实用工具/ 下),
改完后完全退出终端(Cmd+Q)再重开本程序。

热键监听还需要同列表里的「输入监控」,可执行:
   open "x-apple.systempreferences:com.apple.preference.security?Privacy_InputMonitoring"

麦克风无需手动设置,首次录音时系统会弹窗请求。
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
