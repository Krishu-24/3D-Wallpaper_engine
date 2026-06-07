import math


class ExponentialSmoother2D:
    """
    Exponential smoothing with snap threshold and separate axis smoothing.

    Horizontal can stay faster because there are more horizontal views.
    Vertical can be smoothed differently because there are fewer vertical views.
    """

    def __init__(
        self,
        amount=0.55,
        snap_distance=6.0,
        amount_x=None,
        amount_y=None,
    ):
        self.amount = amount
        self.amount_x = amount if amount_x is None else amount_x
        self.amount_y = amount if amount_y is None else amount_y
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

        self.x = self.x + self.amount_x * dx
        self.y = self.y + self.amount_y * dy

        return self.x, self.y

    def get_current(self):
        return self.x, self.y