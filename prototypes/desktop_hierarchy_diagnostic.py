import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

# =========================
# SAFE READ-ONLY WINDOW TOOLS
# =========================

user32.EnumWindows.argtypes = [
    ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM),
    wintypes.LPARAM,
]

user32.EnumChildWindows.argtypes = [
    wintypes.HWND,
    ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM),
    wintypes.LPARAM,
]


def get_class_name(hwnd):
    buffer = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buffer, 256)
    return buffer.value


def get_window_text(hwnd):
    buffer = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, buffer, 512)
    return buffer.value


def get_parent(hwnd):
    return user32.GetParent(hwnd)


def is_window_visible(hwnd):
    return bool(user32.IsWindowVisible(hwnd))


def enum_child_windows(hwnd):
    children = []

    def callback(child_hwnd, lparam):
        children.append(child_hwnd)
        return True

    enum_proc = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HWND,
        wintypes.LPARAM,
    )

    user32.EnumChildWindows(hwnd, enum_proc(callback), 0)
    return children


def enum_top_windows():
    windows = []

    def callback(hwnd, lparam):
        windows.append(hwnd)
        return True

    enum_proc = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HWND,
        wintypes.LPARAM,
    )

    user32.EnumWindows(enum_proc(callback), 0)
    return windows


def print_window(hwnd, indent=0):
    prefix = "  " * indent
    class_name = get_class_name(hwnd)
    title = get_window_text(hwnd)
    parent = get_parent(hwnd)
    visible = is_window_visible(hwnd)

    print(
        f"{prefix}HWND={hwnd} | "
        f"CLASS={class_name!r} | "
        f"TITLE={title!r} | "
        f"PARENT={parent} | "
        f"VISIBLE={visible}"
    )


def print_tree(hwnd, indent=0, max_depth=4):
    print_window(hwnd, indent)

    if indent >= max_depth:
        return

    for child in enum_child_windows(hwnd):
        print_tree(child, indent + 1, max_depth)


def main():
    print("=" * 80)
    print("DESKTOP WINDOW HIERARCHY DIAGNOSTIC")
    print("SAFE MODE: read-only, no window modifications")
    print("=" * 80)

    top_windows = enum_top_windows()

    print("\n[IMPORTANT DESKTOP WINDOWS]\n")

    important_classes = {
        "Progman",
        "WorkerW",
        "SHELLDLL_DefView",
        "SysListView32",
        "CabinetWClass",
        "ApplicationFrameWindow",
        "Shell_TrayWnd",
    }

    for hwnd in top_windows:
        class_name = get_class_name(hwnd)

        if class_name in important_classes:
            print_tree(hwnd, indent=0, max_depth=3)
            print("-" * 80)

    print("\n[ALL PROGMAN / WORKERW TREES]\n")

    for hwnd in top_windows:
        class_name = get_class_name(hwnd)

        if class_name in ["Progman", "WorkerW"]:
            print_tree(hwnd, indent=0, max_depth=5)
            print("-" * 80)

    print("\n[SEARCH RESULTS]\n")

    for hwnd in top_windows:
        class_name = get_class_name(hwnd)

        shell_view = user32.FindWindowExW(
            hwnd,
            0,
            "SHELLDLL_DefView",
            None,
        )

        if shell_view:
            print(f"Found SHELLDLL_DefView under HWND={hwnd}")
            print_window(hwnd, 1)
            print_window(shell_view, 2)

            list_view = user32.FindWindowExW(
                shell_view,
                0,
                "SysListView32",
                None,
            )

            if list_view:
                print("Found SysListView32 desktop icon list:")
                print_window(list_view, 3)

            print("-" * 80)

    print("\n[DONE]")
    print("Copy-paste the full output here.")


if __name__ == "__main__":
    main()
    