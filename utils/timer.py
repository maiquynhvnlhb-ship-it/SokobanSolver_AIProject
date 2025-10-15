
import time
from contextlib import contextmanager

@contextmanager
def timer_ms():
    t0 = time.perf_counter()
    yield lambda: int((time.perf_counter()-t0)*1000)
