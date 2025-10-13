from abc import ABC, abstractmethod


class AbstractPlannerInterface(ABC):
    @abstractmethod
    def create_activity_interface(self) -> None:
        pass

    @abstractmethod
    def create_trip_interface(self) -> None:
        pass

    @abstractmethod
    def create_destination_interface(self) -> None:
        pass

    @abstractmethod
    def remove_trip_interface(self) -> None:
        pass

    @abstractmethod
    def get_all_trips(self) -> None:
        pass

    @abstractmethod
    def get_all_destinations(self) -> None:
        pass

    @abstractmethod
    def get_all_activities(self) -> None:
        pass
