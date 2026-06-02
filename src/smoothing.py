import math


class ExponentialSmoother2D:
    """
    Exponential smoothing with snap threshold.

    Small movement:
    - smooths normally

    Large movement:
    - snaps to the new position so the render does not slowly travel
      through every intermediate frame.
    """

    def __init__(self, amount=0.45, snap_distance=10.0):
        self.amount = amount
        self.snap_distance = snap_distance
        self.x = None
        self.y = None

    def reset(self):
        self.x = None
        self.y = None

    def update(self, new_x, new_y):
        if self.x is None or self.y is None:
            self.x = new_x
            self.y = new_y
            return self.x, self.y

        dx = new_x - self.x
        dy = new_y - self.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance >= self.snap_distance:
            self.x = new_x
            self.y = new_y
            return self.x, self.y

        self.x = self.x + self.amount * dx
        self.y = self.y + self.amount * dy

        return self.x, self.y

    def get_current(self):
        return self.x, self.y