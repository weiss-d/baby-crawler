from typing import Tuple

from asyncio import Queue


class CrawlerQueue(Queue):
    """
    Asycnio queue, that assigns unique ID to each task using simple counter.
    """

    def _init(self, maxsize: int) -> None:
        Queue._init(self, maxsize)
        self.items_added = 0

    def _put(self, item: Tuple[str, int]) -> None:
        """Puts item into queue assigning unique ID to it.

        Parameters
        ----------
        item : Tuple[str, int]
            Tuple containing page URL, page parent unique ID and descendance level.

        Returns
        -------
        None

        """
        self.items_added += 1
        Queue._put(self, (self.items_added, *item))
