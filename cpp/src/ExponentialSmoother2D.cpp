#include "ExponentialSmoother2D.hpp"

#include <cmath>

ExponentialSmoother2D::ExponentialSmoother2D(
    double amount,
    double snapDistance,
    std::optional<double> amountX,
    std::optional<double> amountY)
    : amount_(amount),
      amountX_(amountX.value_or(amount)),
      amountY_(amountY.value_or(amount)),
      snapDistance_(snapDistance) {}

void ExponentialSmoother2D::reset() {
    x_.reset();
    y_.reset();
}

std::pair<double, double> ExponentialSmoother2D::update(double newX, double newY) {
    if (!x_.has_value() || !y_.has_value()) {
        x_ = newX;
        y_ = newY;
        return {*x_, *y_};
    }

    const double dx = newX - *x_;
    const double dy = newY - *y_;
    const double distance = std::sqrt(dx * dx + dy * dy);

    if (distance >= snapDistance_) {
        x_ = newX;
        y_ = newY;
        return {*x_, *y_};
    }

    x_ = *x_ + amountX_ * dx;
    y_ = *y_ + amountY_ * dy;
    return {*x_, *y_};
}

std::pair<std::optional<double>, std::optional<double>> ExponentialSmoother2D::current() const {
    return {x_, y_};
}
