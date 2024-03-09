from publish.EventListeners import EventListeners
from publish.Subject import Subject


class EventManager(Subject):

    def attach(self, observer: EventListeners) -> None:
        print('Subject: Attached an observer to EventManager')
        self._observers.append(observer)

    def detach(self, observer: EventListeners) -> None:
        print('Subject: Detach an observer to EventManager')
        self._observers.remove(observer)

    def notify(self) -> None:
        print("Subject: Notifying observers...")
        for observer in self._observers:
            observer.update(self)
