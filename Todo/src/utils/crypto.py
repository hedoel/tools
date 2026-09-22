"""
本地凭据加解密：基于 Windows 原生 DPAPI (CryptProtectData / CryptUnprotectData)。
密文与当前 Windows 用户账户绑定，换用户或换机器均无法解密，且无需引入额外依赖。
"""
import base64
import ctypes
import sys
from ctypes import wintypes

CRYPTPROTECT_UI_FORBIDDEN = 0x01

# 附加熵值，避免密文被本机其他程序直接解开
_ENTROPY = b"NoOvertime.credential.v1"


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char))
    ]


def is_available() -> bool:
    """当前平台是否支持 DPAPI"""
    return sys.platform == "win32"


def _make_blob(data: bytes):
    """构造 DATA_BLOB，同时返回底层缓冲区以维持其生命周期"""
    buf = ctypes.create_string_buffer(data, len(data))
    blob = _DataBlob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    return blob, buf


def _take_blob(blob: _DataBlob) -> bytes:
    """读取输出 DATA_BLOB 内容并释放其内存"""
    try:
        return ctypes.string_at(blob.pbData, blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(blob.pbData)


def encrypt_secret(plain: str) -> str:
    """加密为 Base64 密文；失败或平台不支持时返回空串 (即不落盘保存)"""
    if not plain or not is_available():
        return ""
    blob_in, _buf_in = _make_blob(plain.encode("utf-8"))
    blob_ent, _buf_ent = _make_blob(_ENTROPY)
    blob_out = _DataBlob()
    try:
        ok = ctypes.windll.crypt32.CryptProtectData(
            ctypes.byref(blob_in), None, ctypes.byref(blob_ent),
            None, None, CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(blob_out)
        )
        if not ok:
            return ""
        return base64.b64encode(_take_blob(blob_out)).decode("ascii")
    except Exception:
        return ""


def decrypt_secret(token: str) -> str:
    """解密 Base64 密文；失败 (密文损坏/换用户/换机器) 时返回空串"""
    if not token or not is_available():
        return ""
    try:
        cipher = base64.b64decode(token.encode("ascii"))
    except Exception:
        return ""

    blob_in, _buf_in = _make_blob(cipher)
    blob_ent, _buf_ent = _make_blob(_ENTROPY)
    blob_out = _DataBlob()
    try:
        ok = ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(blob_in), None, ctypes.byref(blob_ent),
            None, None, CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(blob_out)
        )
        if not ok:
            return ""
        return _take_blob(blob_out).decode("utf-8", errors="ignore")
    except Exception:
        return ""
