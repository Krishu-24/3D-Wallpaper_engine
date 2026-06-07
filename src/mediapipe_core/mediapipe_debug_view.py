import cv2

from mediapipe_core.mediapipe_tracking_worker import get_latest_mediapipe_debug_data


# =========================
# RENDER ANGLE RANGE
# =========================
# Match these to your Blender render script.

Y_ANGLE_MIN = -25.0
Y_ANGLE_MAX = 25.0

Z_ANGLE_MIN = -10.0
Z_ANGLE_MAX = 10.0

START_FRAME = 1


def draw_point(frame, point, label, color):
    if point is None:
        return

    x, y = point

    cv2.circle(frame, (x, y), 5, color, -1)

    cv2.putText(
        frame,
        label,
        (x + 8, y - 8),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        color,
        1,
        cv2.LINE_AA,
    )


def clamp(value, min_value, max_value):
    return max(min_value, min(max_value, value))


def index_to_angle(index, total_views, angle_min, angle_max):
    if total_views is None or total_views <= 1:
        return 0.0

    index = clamp(index, 0, total_views - 1)

    t = index / (total_views - 1)
    return angle_min + t * (angle_max - angle_min)


def index_to_sequence_number(y_index, z_index, y_views, z_views):
    if y_views is None or z_views is None:
        return None

    y_int = int(round(clamp(y_index, 0, y_views - 1)))
    z_int = int(round(clamp(z_index, 0, z_views - 1)))

    flat_index = z_int * y_views + y_int
    frame_number = START_FRAME + flat_index

    return y_int, z_int, frame_number


def create_mediapipe_debug_view(
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

    # Camera center dot
    cv2.circle(debug_frame, (screen_center_x, screen_center_y), 5, (0, 255, 255), -1)

    debug_data = get_latest_mediapipe_debug_data()

    if debug_data is not None and face_box is not None:
        nose = debug_data.get("nose")
        eye_mid = debug_data.get("eye_mid")
        face_center = debug_data.get("face_center")
        forehead = debug_data.get("forehead")
        chin = debug_data.get("chin")
        left_eye_inner = debug_data.get("left_eye_inner")
        right_eye_inner = debug_data.get("right_eye_inner")
        left_eye_outer = debug_data.get("left_eye_outer")
        right_eye_outer = debug_data.get("right_eye_outer")
        tracking_pixel = debug_data.get("tracking_pixel")
        tracking_point = debug_data.get("tracking_point")

        # Important MediaPipe tracking points
        draw_point(debug_frame, nose, "nose", (0, 255, 255))
        draw_point(debug_frame, eye_mid, "eye_mid", (255, 0, 255))
        draw_point(debug_frame, face_center, "face_center", (0, 255, 0))

        # Smaller reference landmarks
        for point in [
            forehead,
            chin,
            left_eye_inner,
            right_eye_inner,
            left_eye_outer,
            right_eye_outer,
        ]:
            if point is not None:
                cv2.circle(debug_frame, point, 2, (255, 255, 255), -1)

        # Main active tracking point
        if tracking_pixel is not None:
            cv2.circle(debug_frame, tracking_pixel, 8, (0, 0, 255), 2)

            cv2.line(
                debug_frame,
                (screen_center_x, screen_center_y),
                tracking_pixel,
                (0, 255, 0),
                2,
            )

        eye_mid_norm = debug_data.get("eye_mid_norm")
        nose_norm = debug_data.get("nose_norm")
        face_center_norm = debug_data.get("face_center_norm")

        cv2.putText(
            debug_frame,
            f"Tracking point: {tracking_point}",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 255, 0),
            2,
        )

        if eye_mid_norm is not None:
            cv2.putText(
                debug_frame,
                f"Eye mid: x={eye_mid_norm[0]:.3f}, y={eye_mid_norm[1]:.3f}",
                (20, 65),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 0, 255),
                2,
            )

        if nose_norm is not None:
            cv2.putText(
                debug_frame,
                f"Nose: x={nose_norm[0]:.3f}, y={nose_norm[1]:.3f}",
                (20, 95),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 255),
                2,
            )

        if face_center_norm is not None:
            cv2.putText(
                debug_frame,
                f"Face center: x={face_center_norm[0]:.3f}, y={face_center_norm[1]:.3f}",
                (20, 125),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 0),
                2,
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

    text_y = 160

    if raw_y_index is not None and raw_z_index is not None:
        raw_y_angle = index_to_angle(
            raw_y_index,
            sequence_y_views,
            Y_ANGLE_MIN,
            Y_ANGLE_MAX,
        )

        raw_z_angle = index_to_angle(
            raw_z_index,
            sequence_z_views,
            Z_ANGLE_MIN,
            Z_ANGLE_MAX,
        )

        raw_sequence_info = index_to_sequence_number(
            raw_y_index,
            raw_z_index,
            sequence_y_views,
            sequence_z_views,
        )

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

        cv2.putText(
            debug_frame,
            f"Raw angle: Y={raw_y_angle:.2f} deg, Z={raw_z_angle:.2f} deg",
            (20, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
        )
        text_y += 30

        if raw_sequence_info is not None:
            raw_y_no, raw_z_no, raw_frame_no = raw_sequence_info

            cv2.putText(
                debug_frame,
                f"Raw image: Y#{raw_y_no + 1}/{sequence_y_views}, Z#{raw_z_no + 1}/{sequence_z_views}, frame={raw_frame_no}",
                (20, text_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
            )
            text_y += 30

    if smoothed_y_index is not None and smoothed_z_index is not None:
        render_y_angle = index_to_angle(
            smoothed_y_index,
            sequence_y_views,
            Y_ANGLE_MIN,
            Y_ANGLE_MAX,
        )

        render_z_angle = index_to_angle(
            smoothed_z_index,
            sequence_z_views,
            Z_ANGLE_MIN,
            Z_ANGLE_MAX,
        )

        render_sequence_info = index_to_sequence_number(
            smoothed_y_index,
            smoothed_z_index,
            sequence_y_views,
            sequence_z_views,
        )

        cv2.putText(
            debug_frame,
            f"Render index: Y={smoothed_y_index:.2f}, Z={smoothed_z_index:.2f}",
            (20, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 255, 255),
            2,
        )
        text_y += 30

        cv2.putText(
            debug_frame,
            f"Render angle: Y={render_y_angle:.2f} deg, Z={render_z_angle:.2f} deg",
            (20, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 255, 255),
            2,
        )
        text_y += 30

        if render_sequence_info is not None:
            render_y_no, render_z_no, render_frame_no = render_sequence_info

            cv2.putText(
                debug_frame,
                f"Render image: Y#{render_y_no + 1}/{sequence_y_views}, Z#{render_z_no + 1}/{sequence_z_views}, frame={render_frame_no}",
                (20, text_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 255),
                2,
            )
            text_y += 30

    if sequence_y_views is not None and sequence_z_views is not None:
        cv2.putText(
            debug_frame,
            f"Sequence grid: {sequence_y_views} x {sequence_z_views}",
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

    return debug_frame