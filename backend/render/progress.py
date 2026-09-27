"""Progress reporting shared by the render steps."""

from collections.abc import Callable

# Called as progress(done, total, stage), e.g. (3, 40, "align")
Progress = Callable[[int, int, str], None]
