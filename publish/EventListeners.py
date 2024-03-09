from __future__ import annotations

from abc import ABC, abstractmethod

from publish import Subject


class EventListeners(ABC):
    """
    The Observer interface declares the update method, used by subjects.
    """
    @abstractmethod
    def update(self, subject: Subject) -> None:
        """
        Receive update from subject.
        """
        pass


class TeleListeners(EventListeners):
    def update(self, subject: Subject) -> None:
        if subject.state < 3:
            print("TeleListeners: Reacted to the event")


class NotionListeners(EventListeners):
    def update(self, subject: Subject) -> None:
        if subject.state > 3:
            print("NotionListeners: Reacted to the event")
