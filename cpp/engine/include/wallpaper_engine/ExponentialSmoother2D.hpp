#pragma once

#include <optional>
#include <utility>

class ExponentialSmoother2D {
public:
    ExponentialSmoother2D(
        double amount = 0.55,
        double snapDistance = 6.0,
        std::optional<double> amountX = std::nullopt,
        std::optional<double> amountY = std::nullopt);

    void reset();
    std::pair<double, double> update(double newX, double newY);
    std::pair<std::optional<double>, std::optional<double>> current() const;

private:
    double amount_;
    double amountX_;
    double amountY_;
    double snapDistance_;
    std::optional<double> x_;
    std::optional<double> y_;
};
