import os
from typing import Callable


def env_getter(name: str) -> Callable[[], str | None]:
    def _ret():
        return os.getenv(name)

    return _ret
