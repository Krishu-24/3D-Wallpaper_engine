import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

# =========================
# SAFE READ-ONLY HELPERS
# =========================

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


def is_visible(hwnd):
    return bool(user32.IsWindowVisible(hwnd))


def get_rect(hwnd):
    rect = wintypes.RECT()
    ok = user32.GetWindowRect(wintypes.HWND(int(hwnd)), ctypes.byref(rect))

    if not ok:
        return None

    return rect.left, rect.top, rect.right, rect.bottom


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

    user32.EnumChildWindows(
        wintypes.HWND(int(hwnd)),
        enum_proc(callback),
        0,
    )

    return children


def print_window(hwnd, indent=0):
    prefix = "  " * indent

    print(
        f"{prefix}HWND={hwnd} | "
        f"CLASS={get_class_name(hwnd)!r} | "
        f"TITLE={get_window_text(hwnd)!r} | "
        f"PARENT={get_parent(hwnd)} | "
        f"VISIBLE={is_visible(hwnd)} | "
        f"RECT={get_rect(hwnd)}"
    )


def print_tree(hwnd, indent=0, max_depth=4):
    print_window(hwnd, indent)

    if indent >= max_depth:
        return

    for child in enum_child_windows(hwnd):
        print_tree(child, indent + 1, max_depth)


# =========================
# MAIN DIAGNOSTIC
# =========================

def main():
    print("=" * 90)
    print("SAFE DESKTOP WALLPAPER DIAGNOSTIC")
    print("READ ONLY: no windows created, no parenting, no Explorer modification")
    print("=" * 90)

    progman = user32.FindWindowW("Progman", None)

    print("\n[1] PROGMAN TREE\n")

    if progman:
        print_tree(progman, max_depth=5)
    else:
        print("[ERROR] Progman not found.")

    print("\n[2] TOP-LEVEL WORKERW WINDOWS\n")

    workerw_count = 0

    for hwnd in enum_top_windows():
        if get_class_name(hwnd) == "WorkerW":
            workerw_count += 1
            print_tree(hwnd, max_depth=2)
            print("-" * 90)

    print(f"\nTotal top-level WorkerW windows: {workerw_count}")

    print("\n[3] DESKTOP ICON LAYER SEARCH\n")

    found_icon_layer = False

    for hwnd in enum_top_windows():
        shell_view = user32.FindWindowExW(
            hwnd,
            0,
            "SHELLDLL_DefView",
            None,
        )

        if shell_view:
            found_icon_layer = True

            print("Found SHELLDLL_DefView:")
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

            print("-" * 90)

    if not found_icon_layer:
        print("[WARN] No SHELLDLL_DefView found under top-level windows.")

    print("\n[4] PROGMAN DIRECT CHILDREN SUMMARY\n")

    if progman:
        for child in enum_child_windows(progman):
            print_window(child, 1)

    print("\n[DONE]")
    print("Copy-paste this output here.")


if __name__ == "__main__":
    main()