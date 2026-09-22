import sys
from PyQt5.QtNetwork import QLocalServer, QLocalSocket
from typing import Callable, Optional


class SingleInstanceGuard:
    """
    单实例保护管理器 (基于 QLocalServer / QLocalSocket IPC 通信):
    1. 防止自启与手动启动、或多次双击产生多个实例冲突；
    2. 后续启动的实例能通过 IPC 管道唤醒已有主窗口，并自身安全退出；
    3. 进程异常终止时，Windows 会自动释放命名管道，不会产生死锁残留。
    """
    def __init__(self, server_name: str = "NoOvertime_Instance_Pipe_Mutex"):
        self.server_name = server_name
        self.server: Optional[QLocalServer] = None

    def is_another_instance_running(self) -> bool:
        """检查是否有已有实例在运行，若有则向其发送 ACTIVATE 信号并返回 True"""
        socket = QLocalSocket()
        socket.connectToServer(self.server_name)
        if socket.waitForConnected(500):
            try:
                socket.write(b"ACTIVATE_WINDOW")
                socket.waitForBytesWritten(500)
                socket.disconnectFromServer()
            except Exception:
                pass
            return True
        return False

    def start_listening(self, on_activate_callback: Callable[[], None]):
        """主实例启动监听服务，用于接收入口重复启动时的唤醒请求"""
        QLocalServer.removeServer(self.server_name)
        self.server = QLocalServer()
        self.server.newConnection.connect(lambda: self._handle_incoming(on_activate_callback))
        self.server.listen(self.server_name)

    def _handle_incoming(self, on_activate_callback: Callable[[], None]):
        if not self.server:
            return
        client = self.server.nextPendingConnection()
        if client:
            if client.waitForReadyRead(500):
                msg = client.readAll().data().decode("utf-8", errors="ignore")
                if "ACTIVATE_WINDOW" in msg:
                    on_activate_callback()
            client.disconnectFromServer()
