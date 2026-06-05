import sys
import ctypes
from ctypes import wintypes

from PyQt5.QtWidgets import QApplication, QLabel
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

user32 = ctypes.windll.user32

LONG_PTR = ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long

user32.GetWindowLongPtrW.restype = LONG_PTR
user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]

user32.SetWindowLongPtrW.restype = LONG_PTR
user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, LONG_PTR]

user32.SetWindowPos.restype = wintypes.BOOL
user32.SetWindowPos.argtypes = [
    wintypes.HWND,
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_uint,
]

GWL_EXSTYLE = -20
GWLP_HWNDPARENT = -8

WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
WS_EX_APPWINDOW = 0x00040000

SWP_SHOWWINDOW = 0x0040
SWP_FRAMECHANGED = 0x0020
SWP_NOACTIVATE = 0x0010

HWND_BOTTOM = wintypes.HWND(1)


def key_down(vk):
    return user32.GetAsyncKeyState(vk) & 0x8000


def quit_pressed():
    # Ctrl + Alt + Q or F12
    return (
        (key_down(0x11) and key_down(0x12) and key_down(0x51))
        or key_down(0x7B)
    )


def find_shelldll_defview():
    progman = user32.FindWindowW("Progman", None)

    found = user32.FindWindowExW(
        progman,
        0,
        "SHELLDLL_DefView",
        None,
    )

    if found:
        return found

    def enum_callback(hwnd, lparam):
        nonlocal found

        candidate = user32.FindWindowExW(
            hwnd,
            0,
            "SHELLDLL_DefView",
            None,
        )

        if candidate:
            found = candidate
            return False

        return True

    enum_proc = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HWND,
        wintypes.LPARAM,
    )

    user32.EnumWindows(enum_proc(enum_callback), 0)

    return found


def attach_as_desktop_owned_window(hwnd):
    hwnd = wintypes.HWND(int(hwnd))
    defview = find_shelldll_defview()

    if not defview:
        print("[ERROR] Could not find SHELLDLL_DefView.")
        return False

    defview = wintypes.HWND(int(defview))

    screen_w = user32.GetSystemMetrics(0)
    screen_h = user32.GetSystemMetrics(1)

    # Do NOT SetParent.
    # Set the desktop icon view as owner instead.
    user32.SetWindowLongPtrW(
        hwnd,
        GWLP_HWNDPARENT,
        LONG_PTR(defview.value),
    )

    exstyle = int(user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE))
    exstyle &= ~WS_EX_APPWINDOW
    exstyle |= WS_EX_TOOLWINDOW
    exstyle |= WS_EX_NOACTIVATE

    user32.SetWindowLongPtrW(
        hwnd,
        GWL_EXSTYLE,
        LONG_PTR(exstyle),
    )

    user32.SetWindowPos(
        hwnd,
        HWND_BOTTOM,
        0,
        0,
        screen_w,
        screen_h,
        SWP_SHOWWINDOW | SWP_FRAMECHANGED | SWP_NOACTIVATE,
    )

    print(f"[INFO] Attached using owner mode. SHELLDLL_DefView={defview.value}")
    return True


class TestWindow(QLabel):
    def __init__(self):
        super().__init__()

        screen_w = user32.GetSystemMetrics(0)
        screen_h = user32.GetSystemMetrics(1)

        self.setWindowTitle("PyQt Wallpaper Owner Mode Test")
        self.setGeometry(0, 0, screen_w, screen_h)

        self.setAttribute(Qt.WA_NativeWindow, True)
        self.setAttribute(Qt.WA_DontCreateNativeAncestors, True)

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.Tool
        )

        self.setAlignment(Qt.AlignCenter)

        font = QFont()
        font.setPointSize(26)
        font.setBold(True)
        self.setFont(font)

        self.setStyleSheet("""
            QLabel {
                background-color: rgb(20, 40, 90);
                color: white;
            }
        """)

        self.setText(
            "PYQT OWNER MODE TEST\n\n"
            "Expected:\n"
            "Old wallpaper hidden\n"
            "Desktop icons visible above this\n"
            "Right click still works\n\n"
            "Quit: Ctrl + Alt + Q or F12\n"
            "Emergency: taskkill /F /IM python.exe"
        )

        self.timer = QTimer()
        self.timer.timeout.connect(self.check_quit)
        self.timer.start(80)

    def check_quit(self):
        if quit_pressed():
            QApplication.quit()


def main():
    print("[INFO] Starting owner-mode wallpaper test.")
    print("[INFO] Quit: Ctrl + Alt + Q or F12")
    print("[INFO] Emergency kill: taskkill /F /IM python.exe")

    app = QApplication(sys.argv)

    window = TestWindow()
    window.show()

    QTimer.singleShot(
        500,
        lambda: attach_as_desktop_owned_window(window.winId()),
    )

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()