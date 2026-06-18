import math
from typing import Callable


class LCG:
    """Custom linear congruential generator (uniform on [0,1)).
    """
    def __init__(self, seed: int = 42, a: int = 1103515245,
                 c: int = 12345, m: int = 2 ** 31):
        self.a, self.c, self.m = a, c, m
        self.state = seed % m

    def random(self) -> float:
        """Next uniform draw on [0, 1)."""
        self.state = (self.a * self.state + self.c) % self.m
        return self.state / self.m


def exponential(rate: float, rng: LCG) -> Callable[[], float]:
    """M (Markovian) sampler: inter-event times ~ Exp(rate), mean = 1/rate.

    Inverse-transform of a custom-LCG uniform u:  t = -ln(1 - u) / rate.
    """
    return lambda: -math.log(1.0 - rng.random()) / rate


def deterministic(value: float) -> Callable[[], float]:
    """D (Deterministic) sampler: constant value."""
    return lambda: value


def lognormal(mean: float, cv: float, rng: LCG) -> Callable[[], float]:
    """G (General) sampler: log-normal service times (report SD_01).

    Parametrised by the *target* mean and coefficient of variation
    (cv = std / mean) of the resulting positive variable, which is the
    natural way to describe right-skewed HPC runtimes.

    The underlying normal parameters are derived from (mean, cv):
        sigma^2 = ln(1 + cv^2)
        mu      = ln(mean) - sigma^2 / 2
    A standard normal Z is produced from two custom-LCG uniforms by the
    Box-Muller transform, then the sample is exp(mu + sigma * Z).
    """
    if mean <= 0:
        raise ValueError("lognormal mean must be > 0")
    if cv < 0:
        raise ValueError("lognormal cv must be >= 0")
    sigma2 = math.log(1.0 + cv * cv)
    sigma = math.sqrt(sigma2)
    mu = math.log(mean) - sigma2 / 2.0

    def sample() -> float:
        u1 = rng.random()
        u2 = rng.random()
        z = math.sqrt(-2.0 * math.log(1.0 - u1)) * math.cos(2.0 * math.pi * u2)
        return math.exp(mu + sigma * z)

    return sample
