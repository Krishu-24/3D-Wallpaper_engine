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


def face_box_to_sequence_indices(
    face_box,
    camera_width,
    camera_height,
    y_views,
    z_views,
    flip_x=False,
    flip_z=True,
):
    """
    Converts face rectangle coordinates into floating-point sequence indices.

    face_box format:
    (x, y, w, h)

    Output:
    y_float, z_float
    """

    x, y, w, h = face_box

    face_center_x = x + w / 2
    face_center_y = y + h / 2

    if flip_x:
        y_float = map_range(
            face_center_x,
            0,
            camera_width,
            y_views - 1,
            0,
        )
    else:
        y_float = map_range(
            face_center_x,
            0,
            camera_width,
            0,
            y_views - 1,
        )

    if flip_z:
        z_float = map_range(
            face_center_y,
            0,
            camera_height,
            z_views - 1,
            0,
        )
    else:
        z_float = map_range(
            face_center_y,
            0,
            camera_height,
            0,
            z_views - 1,
        )

    return y_float, z_float