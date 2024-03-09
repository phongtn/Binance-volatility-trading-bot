from __future__ import annotations

from abc import abstractmethod, ABC
from typing import List

from publish import EventListeners


class Subject(ABC):
    """
    The Subject owns some important state and notifies observers when the state changes.
    """
    _state: int = None
    """
    For the sake of simplicity, the Subject's state, essential to all
    subscribers, is stored in this variable.
    """
    _observers: List[EventListeners] = []
    """
    List of subscribers. In real life, the list of subscribers can be stored
    more comprehensively (categorized by event type, etc.).
    """

    @abstractmethod
    def attach(self, observer: EventListeners) -> None:
        """
        Attach an observer to the subject.
        """
        pass

    @abstractmethod
    def detach(self, observer: EventListeners) -> None:
        """
        Detach an observer from the subject.
        """
        pass

    @abstractmethod
    def notify(self) -> None:
        """
        Notify all observers about an event.
        """
        pass

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        self._state = value
