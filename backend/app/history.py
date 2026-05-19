import threading
from collections import deque
from typing import List


class HistoryStore:
    """Armazena os últimos N resultados de detecção em memória."""

    def __init__(self, max_size: int = 100):
        self._lock = threading.Lock()
        self._data: deque = deque(maxlen=max_size)

    def add(self, result: dict):
        with self._lock:
            self._data.appendleft(result)

    def get_all(self) -> List[dict]:
        with self._lock:
            return list(self._data)

    def clear(self):
        with self._lock:
            self._data.clear()


history_store = HistoryStore()
