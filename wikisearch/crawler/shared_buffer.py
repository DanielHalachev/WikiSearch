import queue
from typing import Tuple


class SharedBuffer:
    def __init__(self, limit):
        self.queue = queue.Queue(maxsize=limit)

    def put(self, item: Tuple[int, str, str]):
        self.queue.put(item)

    def pop(self):
        """Gets item from the queue, blocking if the queue is empty"""
        return self.queue.get()

    def task_done(self):
        """Indicates that a task is done"""
        self.queue.task_done()
