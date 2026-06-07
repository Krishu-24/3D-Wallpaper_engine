import cv2
import numpy as np


def create_debug_view(
    frame,
    face_box,
    raw_y_index=None,
    raw_z_index=None,
    smoothed_y_index=None,
    smoothed_z_index=None,
    cache_info=None,
    sequence_y_views=None,
    sequence_z_views=None,
    tracking_frame_id=None,
):
    debug_frame = frame.copy()
    h, w = debug_frame.shape[:2]

    screen_center_x = w // 2
    screen_center_y = h // 2

    # Center guide lines
    cv2.line(debug_frame, (screen_center_x, 0), (screen_center_x, h), (80, 80, 80), 1)
    cv2.line(debug_frame, (0, screen_center_y), (w, screen_center_y), (80, 80, 80), 1)

    # Quarter guide lines
    cv2.line(debug_frame, (w // 4, 0), (w // 4, h), (45, 45, 45), 1)
    cv2.line(debug_frame, ((3 * w) // 4, 0), ((3 * w) // 4, h), (45, 45, 45), 1)
    cv2.line(debug_frame, (0, h // 4), (w, h // 4), (45, 45, 45), 1)
    cv2.line(debug_frame, (0, (3 * h) // 4), (w, (3 * h) // 4), (45, 45, 45), 1)

    # Center dot
    cv2.circle(debug_frame, (screen_center_x, screen_center_y), 5, (0, 255, 255), -1)

    face_crop_panel = np.zeros((180, 240, 3), dtype=np.uint8)

    if face_box is not None:
        x, y, fw, fh = face_box

        face_center_x = int(x + fw / 2)
        face_center_y = int(y + fh / 2)

        cv2.rectangle(
            debug_frame,
            (x, y),
            (x + fw, y + fh),
            (255, 255, 0),
            2,
        )

        cv2.circle(
            debug_frame,
            (face_center_x, face_center_y),
            6,
            (0, 255, 255),
            -1,
        )

        cv2.line(
            debug_frame,
            (screen_center_x, screen_center_y),
            (face_center_x, face_center_y),
            (0, 255, 0),
            2,
        )

        cv2.putText(
            debug_frame,
            f"Face center: ({face_center_x}, {face_center_y})",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 255, 0),
            2,
        )

        cv2.putText(
            debug_frame,
            f"Face size: {fw} x {fh}",
            (20, 65),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 255, 0),
            2,
        )

        pad = 20
        x0 = max(0, x - pad)
        y0 = max(0, y - pad)
        x1 = min(w, x + fw + pad)
        y1 = min(h, y + fh + pad)

        crop = frame[y0:y1, x0:x1]

        if crop.size > 0:
            face_crop_panel = cv2.resize(
                crop,
                (240, 180),
                interpolation=cv2.INTER_AREA,
            )
    else:
        cv2.putText(
            debug_frame,
            "No face detected - holding last render position",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 255),
            2,
        )

    text_y = 100

    if raw_y_index is not None and raw_z_index is not None:
        cv2.putText(
            debug_frame,
            f"Raw index: Y={raw_y_index:.2f}, Z={raw_z_index:.2f}",
            (20, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
        )
        text_y += 30

    if smoothed_y_index is not None and smoothed_z_index is not None:
        cv2.putText(
            debug_frame,
            f"Render index: Y={smoothed_y_index:.2f}, Z={smoothed_z_index:.2f}",
            (20, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
        )
        text_y += 30

    if sequence_y_views is not None and sequence_z_views is not None:
        cv2.putText(
            debug_frame,
            f"Sequence: {sequence_y_views} x {sequence_z_views}",
            (20, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
        )
        text_y += 30

    if cache_info is not None:
        cv2.putText(
            debug_frame,
            f"Cache: {cache_info['cached_frames']}/{cache_info['max_cache_size']}",
            (20, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 255, 0),
            2,
        )
        text_y += 30

        cv2.putText(
            debug_frame,
            f"Loading: {cache_info['loading_frames']}",
            (20, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 255, 0),
            2,
        )
        text_y += 30

    if tracking_frame_id is not None:
        cv2.putText(
            debug_frame,
            f"Tracking frame id: {tracking_frame_id}",
            (20, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
        )
        text_y += 30

    cv2.putText(
        debug_frame,
        "ESC: quit",
        (20, h - 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 255),
        2,
    )

    # Grayscale panel
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    gray_panel = cv2.resize(gray_bgr, (240, 180), interpolation=cv2.INTER_AREA)

    cv2.putText(
        gray_panel,
        "Grayscale",
        (10, 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (0, 255, 255),
        2,
    )

    cv2.putText(
        face_crop_panel,
        "Tracked Face",
        (10, 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (0, 255, 255),
        2,
    )

    panel_margin = 20
    panel_x = max(0, w - 240 - panel_margin)

    if h > 420:
        debug_frame[panel_margin:panel_margin + 180, panel_x:panel_x + 240] = gray_panel
        debug_frame[
            panel_margin + 200:panel_margin + 380,
            panel_x:panel_x + 240,
        ] = face_crop_panel

    return debug_frame