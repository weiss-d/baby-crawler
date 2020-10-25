"""Asycnio queue, that stores all tasks ever added.

Popular solution for multitask crawling from
https://stackoverflow.com/questions/1581895/how-check-if-a-task-is-already-in-python-queue
"""
from asyncio import Queue


class SetQueue(Queue):
    def _init(self, maxsize):
        Queue._init(self, maxsize)
        self.all_items = set()

    def _put(self, item):
        if item not in self.all_items:
            Queue._put(self, item)
            self.all_items.add(item)


# class CrawlerQueue(Queue):
#
#     def _init(self, maxsize):
#         Queue._init(sefl, maxsize)
#
#         self.all_items = set()
#         self.items_added = 0
#
#     def _put(self, item):
#         if not item in self.all_items:
#             self.items_added +=1
#             Queue._put(self, (item, self.items_added))
#             self.all_items.add(item)
