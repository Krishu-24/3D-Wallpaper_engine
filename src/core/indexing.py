import math


def clamp(value, min_value, max_value):
    return max(min_value, min(max_value, value))


def map_range(value, in_min, in_max, out_min, out_max):
    """
    Maps a value from one range to another.
    """

    if in_max == in_min:
        return out_min

    value = clamp(value, in_min, in_max)

    t = (value - in_min) / (in_max - in_min)
    return out_min + t * (out_max - out_min)


def pixel_to_camera_angle(
    pixel_value,
    image_size,
    camera_fov_degrees,
    center_positive_direction=1,
):
    """
    Converts a pixel coordinate into a real camera angle.

    This uses pinhole-camera geometry instead of simple linear pixel mapping.

    For horizontal:
        center_positive_direction = 1

        left side  -> negative angle
        center     -> 0 degrees
        right side -> positive angle

    For vertical:
        center_positive_direction = -1 if image y increases downward
        and you want upward movement to be positive.

        top        -> positive angle
        center     -> 0 degrees
        bottom     -> negative angle
    """

    if image_size <= 0:
        return 0.0

    half_size = image_size / 2.0

    if half_size == 0:
        return 0.0

    normalized_offset = (pixel_value - half_size) / half_size
    normalized_offset *= center_positive_direction

    half_fov_rad = math.radians(camera_fov_degrees / 2.0)

    angle_rad = math.atan(normalized_offset * math.tan(half_fov_rad))
    angle_deg = math.degrees(angle_rad)

    return angle_deg


def angle_to_sequence_index(
    angle_degrees,
    angle_min,
    angle_max,
    total_views,
):
    """
    Converts a render angle into a floating-point sequence index.

    Example:
        angle_min = -25
        angle_max = 25
        total_views = 121

        -25 deg -> 0
          0 deg -> 60
        +25 deg -> 120
    """

    if total_views <= 1:
        return 0.0

    return map_range(
        angle_degrees,
        angle_min,
        angle_max,
        0,
        total_views - 1,
    )


def face_box_to_camera_angles(
    face_box,
    camera_width,
    camera_height,
    camera_horizontal_fov=54.3,
    camera_vertical_fov=40.7,
    flip_x=False,
    flip_z=True,
):
    """
    Converts face_box center into real camera angles.

    face_box format:
        (x, y, w, h)

    Output:
        camera_y_angle, camera_z_angle

    Convention:
        Y angle:
            left  = negative
            right = positive

        Z angle:
            up    = positive
            down  = negative
    """

    x, y, w, h = face_box

    face_center_x = x + w / 2.0
    face_center_y = y + h / 2.0

    camera_y_angle = pixel_to_camera_angle(
        pixel_value=face_center_x,
        image_size=camera_width,
        camera_fov_degrees=camera_horizontal_fov,
        center_positive_direction=1,
    )

    camera_z_angle = pixel_to_camera_angle(
        pixel_value=face_center_y,
        image_size=camera_height,
        camera_fov_degrees=camera_vertical_fov,
        center_positive_direction=-1,
    )

    if flip_x:
        camera_y_angle *= -1

    # Old config uses flip_z=True because image y increases downward.
    # With the new angle convention, upward is already positive.
    # So flip_z=True means keep the correct physical direction.
    # flip_z=False reverses it.
    if not flip_z:
        camera_z_angle *= -1

    return camera_y_angle, camera_z_angle


def face_box_to_sequence_indices(
    face_box,
    camera_width,
    camera_height,
    y_views,
    z_views,
    flip_x=False,
    flip_z=True,
    camera_horizontal_fov=54.3,
    camera_vertical_fov=40.7,
    render_y_angle_min=-25.0,
    render_y_angle_max=25.0,
    render_z_angle_min=-10.0,
    render_z_angle_max=10.0,
):
    """
    Converts face rectangle coordinates into floating-point sequence indices
    using camera FOV and rendered angle range.

    This is angle matching, not simple pixel matching.

    Pipeline:
        face_box center
        -> camera angle using webcam FOV
        -> rendered angle range
        -> sequence index

    face_box format:
        (x, y, w, h)

    Output:
        y_float, z_float
    """

    camera_y_angle, camera_z_angle = face_box_to_camera_angles(
        face_box=face_box,
        camera_width=camera_width,
        camera_height=camera_height,
        camera_horizontal_fov=camera_horizontal_fov,
        camera_vertical_fov=camera_vertical_fov,
        flip_x=flip_x,
        flip_z=flip_z,
    )

    y_float = angle_to_sequence_index(
        angle_degrees=camera_y_angle,
        angle_min=render_y_angle_min,
        angle_max=render_y_angle_max,
        total_views=y_views,
    )

    z_float = angle_to_sequence_index(
        angle_degrees=camera_z_angle,
        angle_min=render_z_angle_min,
        angle_max=render_z_angle_max,
        total_views=z_views,
    )

    return y_float, z_float