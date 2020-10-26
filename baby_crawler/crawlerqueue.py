"""Asycnio queue, that stores all tasks ever added assigning unique ID to each task.

Combined with popular solution for multitask crawling from
https://stackoverflow.com/questions/1581895/how-check-if-a-task-is-already-in-python-queue
"""
from typing import Tuple

from asyncio import Queue


class CrawlerQueue(Queue):
    def _init(self, maxsize: int) -> None:
        Queue._init(self, maxsize)

        self.all_items = set()
        self.items_added = 0

    def _put(self, item: Tuple[str, int]) -> None:
        """Puts item into queue assigning unique ID to it.

        Parameters
        ----------
        item : Tuple[str, int]
            Tuple containing page URL and page parent unique ID.

        Returns
        -------
        None

        """
        if not item in self.all_items:
            self.items_added += 1
            Queue._put(self, (self.items_added, *item))
            self.all_items.add(item)
