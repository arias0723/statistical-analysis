import random
from typing import Callable


def exponential(rate: float) -> Callable[[], float]:
    return lambda: random.expovariate(rate)

def deterministic(value: float) -> Callable[[], float]:
    return lambda: value
