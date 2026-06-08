import math
import random
from typing import Callable


def exponential(rate: float) -> Callable[[], float]:
    """M (Markovian) sampler: inter-event times ~ Exp(rate), mean = 1/rate."""
    return lambda: random.expovariate(rate)


def deterministic(value: float) -> Callable[[], float]:
    """D (Deterministic) sampler: constant value."""
    return lambda: value


def lognormal(mean: float, cv: float) -> Callable[[], float]:
    """G (General) sampler: log-normal service times.

    Parametrised by the *target* mean and coefficient of variation
    (cv = std / mean) of the resulting positive variable, which is the
    natural way to describe right-skewed HPC runtimes (report SD_01).

    The underlying normal parameters are derived from (mean, cv):
        sigma^2 = ln(1 + cv^2)
        mu      = ln(mean) - sigma^2 / 2
    """
    if mean <= 0:
        raise ValueError("lognormal mean must be > 0")
    if cv < 0:
        raise ValueError("lognormal cv must be >= 0")
    sigma2 = math.log(1.0 + cv * cv)
    sigma = math.sqrt(sigma2)
    mu = math.log(mean) - sigma2 / 2.0
    return lambda: math.exp(random.gauss(mu, sigma))
