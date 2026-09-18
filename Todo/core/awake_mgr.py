import ctypes
from datetime import datetime, timedelta
from typing import Optional
from PyQt5.QtCore import QObject, QTimer, pyqtSignal

# Windows 电源管理 API 状态标识
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002


class AwakeManager(QObject):
    """屏幕常亮与防休眠管理器 (基于 Windows 原生 SetThreadExecutionState API)"""
    state_changed = pyqtSignal(bool, str)  # (是否激活, 状态文字说明)
    time_tick = pyqtSignal(int)  # 剩余秒数
    expired = pyqtSignal()  # 倒计时结束信号

    _instance: Optional['AwakeManager'] = None

    @classmethod
    def get_instance(cls) -> 'AwakeManager':
        if cls._instance is None:
            cls._instance = AwakeManager()
        return cls._instance

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_active = False
        self.mode = "indefinite"  # "indefinite" (常开) 或 "timed" (定时)
        self.target_hours = 2
        self.end_time: Optional[datetime] = None

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._on_tick)

    def enable(self, mode: str = "indefinite", hours: int = 2):
        """启用防息屏模式"""
        self.mode = mode
        self.target_hours = hours
        if mode == "timed":
            self.end_time = datetime.now() + timedelta(hours=hours)
            self.timer.start()
        else:
            self.end_time = None
            self.timer.stop()

        # 调用 Windows 原生内核 API，阻止屏幕息屏和系统休眠
        flags = ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
        ret = ctypes.windll.kernel32.SetThreadExecutionState(flags)
        self.is_active = (ret != 0)
        self._emit_state()

    def disable(self):
        """关闭防息屏，复原系统正常休眠策略"""
        self.is_active = False
        self.end_time = None
        self.timer.stop()
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        self._emit_state()

    def _on_tick(self):
        if not self.is_active or not self.end_time:
            self.timer.stop()
            return

        now = datetime.now()
        if now >= self.end_time:
            self.disable()
            self.expired.emit()
            return

        rem_secs = int((self.end_time - now).total_seconds())
        self.time_tick.emit(rem_secs)
        self._emit_state()

    def remaining_seconds(self) -> int:
        if not self.is_active or not self.end_time:
            return 0
        rem = int((self.end_time - datetime.now()).total_seconds())
        return max(0, rem)

    def get_status_text(self) -> str:
        if not self.is_active:
            return "未开启"
        if self.mode == "indefinite":
            return "持续常亮中 (直到手动关闭)"
        rem = self.remaining_seconds()
        h = rem // 3600
        m = (rem % 3600) // 60
        s = rem % 60
        return f"定时防息屏中 (剩余 {h:02d}:{m:02d}:{s:02d})"

    def _emit_state(self):
        self.state_changed.emit(self.is_active, self.get_status_text())

    def cleanup(self):
        self.disable()
