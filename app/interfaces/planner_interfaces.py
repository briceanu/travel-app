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

    @abstractmethod
    def all_users_enlisted_in_a_specific_trip(self) -> None:
        pass

    @abstractmethod
    def trips_with_participant(self) -> None:
        pass

    @abstractmethod
    def destinations_with_more_than_a_specified_nr_activities(self) -> None:
        pass

    @abstractmethod
    def fetch_users_by_birth_date(self) -> None:
        pass

    @abstractmethod
    def get_user_enrolled_activities(self) -> None:
        pass

    @abstractmethod
    def get_trips_for_users_born_before(self) -> None:
        pass

    @abstractmethod
    def get_activities_by_destination(self) -> None:
        pass

    @abstractmethod
    def get_activities_by_trip(self) -> None:
        pass

    @abstractmethod
    def fetch_destinations_after_activity_start_time(self) -> None:
        pass

    @abstractmethod
    def activities_in_a_specified_interval(self) -> None:
        pass

    @abstractmethod
    def total_cost_of_activities_per_destination(self) -> None:
        pass

    @abstractmethod
    def most_expensive_activity_per_destination(self) -> None:
        pass

    @abstractmethod
    async def get_users_in_trips_with_expensive_activities(self) -> None:
        pass

    @abstractmethod
    async def most_expensive_trips(self) -> None:
        pass

    @abstractmethod
    async def get_trips_by_popularity(self) -> None:
        pass

    @abstractmethod
    async def get_destination_with_most_activities(self) -> None:
        pass

    @abstractmethod
    async def average_price_of_activities_in_each_destination(self) -> None:
        pass
