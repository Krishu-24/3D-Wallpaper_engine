class NormalizedGridMapper:
    """
    Maps normalized x/y coordinates into a 2D image sequence grid.

    Example:
        Y_VIEWS = 121
        Z_VIEWS = 35

        y_index = 0 to 120
        z_index = 0 to 34

        frame_index = z_index * Y_VIEWS + y_index
    """

    def __init__(
        self,
        y_views,
        z_views,
        invert_y=False,
        invert_z=False,
        deadzone_x=0.0,
        deadzone_y=0.0,
    ):
        self.y_views = y_views
        self.z_views = z_views
        self.invert_y = invert_y
        self.invert_z = invert_z
        self.deadzone_x = deadzone_x
        self.deadzone_y = deadzone_y

    @staticmethod
    def clamp01(value):
        return max(0.0, min(1.0, value))

    @staticmethod
    def apply_center_deadzone(value, deadzone):
        """
        Keeps value centered around 0.5 if movement is tiny.

        Useful later if the wallpaper jitters near the center.
        deadzone = 0.02 means values from 0.48 to 0.52 become 0.5.
        """

        if deadzone <= 0.0:
            return value

        center = 0.5

        if abs(value - center) <= deadzone:
            return center

        return value

    def normalized_to_index(self, value, num_views, invert=False):
        value = self.clamp01(value)

        if invert:
            value = 1.0 - value

        index = round(value * (num_views - 1))
        index = max(0, min(num_views - 1, index))

        return index

    def map(self, x, y):
        """
        Takes normalized tracker x/y and returns:
            y_index, z_index, frame_index
        """

        x = self.clamp01(x)
        y = self.clamp01(y)

        x = self.apply_center_deadzone(x, self.deadzone_x)
        y = self.apply_center_deadzone(y, self.deadzone_y)

        y_index = self.normalized_to_index(
            x,
            self.y_views,
            invert=self.invert_y,
        )

        z_index = self.normalized_to_index(
            y,
            self.z_views,
            invert=self.invert_z,
        )

        frame_index = self.grid_to_frame_index(y_index, z_index)

        return y_index, z_index, frame_index

    def grid_to_frame_index(self, y_index, z_index):
        return z_index * self.y_views + y_index