from app.repositories.planner_repository import PlannerRepository


class PlannerService:
    """
    Service layer responsible for managing planner-related business logic.

    This class acts as an intermediary between the API layer and the data access
    layer (repository). It defines high-level operations for managing activities
    while delegating database interactions to the PlannerRepository.
    """

    def __init__(self, repository: PlannerRepository):
        """
        Initialize the PlannerService with a repository instance.

        Args:
            repository (PlannerRepository): An instance of the PlannerRepository
                responsible for handling database operations related to activities.
        """
        self.repository = repository

    async def add_activity(self):
        """
        Create and persist a new activity using the planner repository.

        This method delegates the actual database interaction to the repository
        layer and returns the result of the creation operation.

        Returns:
            Any: The created activity object or the result returned by the repository.
        """
        return await self.repository.create_activity_interface()

    async def add_trip(self):
        """
        Create and persist a new trip using the planner repository.

        This method delegates the creation of the trip to the repository layer,
        which handles the database interaction. It returns the result of the
        creation operation, typically the newly created trip object.

        Returns:
            Any: The created trip object or the result returned by the repository.
        """
        return await self.repository.create_trip_interface()

    async def add_destination(self):
        """
        Create and persist a new destination using the planner repository.

        This method delegates the creation of the destination to the repository layer,
        which handles the database interaction. It returns the result of the
        creation operation, typically the newly created destination object.

        Returns:
            Any: The created destination object or the result returned by the repository.
        """
        return await self.repository.create_destination_interface()

    async def delete_trip(self):
        """
        Delete an existing trip record.

        This method delegates the deletion process to the repository layer,
        which performs the actual database operation to remove the trip
        identified by the current context or request parameters.

        Returns:
            Any: The result or confirmation message returned by
            `remove_trip_interface()` from the repository layer.

        Raises:
            HTTPException: If the specified trip cannot be found or
            an error occurs during the deletion process.
        """
        return await self.repository.remove_trip_interface()

    async def all_trips(self):
        """
        Retrieve all trips from the repository.

        This method delegates to the repository layer's `get_all_trips` method
        to fetch all trip records, including their nested destinations and activities.

        Returns:
        list[TripSchemaOut]: A list of trips with their destinations and activities.
        """
        return await self.repository.get_all_trips()

    async def all_destinations(self):
        """
        Retrieve all destinations from the repository.

        This method delegates to the repository layer's `get_all_destinations` method
        to fetch all destination records, including their related activities if included
        in the repository query.

        Returns:
            list[DestinationSchemaOut]: A list of destinations with their details
            and associated activities.
        """
        return await self.repository.get_all_destinations()

    async def all_activities(self):
        """
        Retrieve all activities from the repository.

        This method delegates to the repository layer's `get_all_activities` method
        to fetch all activity records, including details such as name, description,
        start and end times, price, and associated destination ID.

        Returns:
            list[ActivitySchemaOut]: A list of activity objects with their details
            and associated destination information.
        """
        return await self.repository.get_all_activities()

    async def get_users_registered_for_trip(self):
        """
        Retrieve all users who are registered for a specific trip.

        Returns:
            list: A list of user objects (or serialized representations) enlisted in the specified trip.
        """
        return await self.repository.all_users_enlisted_in_a_specific_trip()

    async def fetch_trips_with_participants(self):
        """
        Retrieve all trips along with their associated participants.

        This method delegates the query to the repository layer, which fetches
        trips and includes the participants for each trip.

        Returns:
            list: A list of trip objects, each containing its participants.
        """
        return await self.repository.trips_with_participant()

    async def fetch_destinations_with_nr_of_participants(self):
        """
        Retrieve destinations that have a minimum number of associated activities or participants.

        This method delegates the query to the repository layer, which fetches
        destinations meeting the specified criteria for the number of activities
        or participants.

        Returns:
            list: A list of destination objects that satisfy the minimum number of activities/participants.
        """
        return await self.repository.destinations_with_more_than_a_specified_nr_activities()

    async def get_users_by_birth_date(self):
        """
        Retrieve users whose date of birth is later than the specified cutoff date.

        This service method delegates the database query to the repository layer and
        returns a list of user profiles that meet the filtering criteria. It serves as
        the business logic layer between the FastAPI route and the repository.

        Returns:
            list[user_schemas.UserProfileSchemaOut]:
                A list of user profile schemas representing users whose
                `date_of_birth` is greater than the value defined in the repository.

        Raises:
            HTTPException:
                If an error occurs in the repository or during data retrieval.
        """
        return await self.repository.fetch_users_by_birth_date()

    async def find_user_activities(self):
        """
        Retrieve all activities in which the current user is enrolled.

        This service method delegates the data retrieval to the repository layer,
        returning a list of activities associated with the user. It acts as the
        business logic layer between the API route and the repository.

        Returns:
            list[Activity]:
                A list of activity objects representing all activities the user
                is currently enrolled in.

        Raises:
            HTTPException:
                If an error occurs during data retrieval from the repository.
        """

        return await self.repository.get_user_enrolled_activities()

    async def find_trips_by_user_birth_date(self):
        """
        Retrieve trips associated with users born before a specified date.

        This service method delegates the query to the repository layer, which performs
        a subquery to select users with a `date_of_birth` earlier than the specified cutoff.
        It then retrieves all trips those users are enrolled in, ensuring duplicates are
        removed, and maps the results to `TripSchemaOut` schemas for structured output.

        Returns:
            list[planner_schemas.TripSchemaOut]:
                A list of trip schemas containing details such as trip ID, title,
                description, type, start and end dates, duration, estimated budget,
                and empty placeholders for destinations and participants.

        Raises:
            HTTPException:
                If any error occurs during database access or data processing.

        """
        return await self.repository.get_trips_for_users_born_before()

    async def fetch_activities_by_destination(self):
        """
        Retrieve all activities grouped or associated with their respective destinations.

        This service method delegates the database query to the repository layer,
        which fetches activity data along with destination relationships. It returns
        a structured list of activities, each linked to the corresponding destination.

        Returns:
            list[planner_schemas.ActivitySchemaOut]:
                A list of activity objects containing details such as name, description,
                start and end times, duration, price, and destination linkage information.

        Raises:
            HTTPException:
                If any unexpected error occurs during data retrieval or processing.
        """

        return await self.repository.get_activities_by_destination()

    async def fetch_activities_by_trip(self):
        """
        Retrieve all activities associated with their respective trips.

        This service method delegates the query logic to the repository layer,
        which fetches activities linked to trips—either directly or through
        related destinations. It returns a structured list of activities
        belonging to each trip.

        Returns:
            list[planner_schemas.ActivitySchemaOut]:
                A list of activity objects containing fields such as name, description,
                start and end times, duration, price, and trip association details.

        Raises:
            HTTPException:
                If an unexpected error occurs during data retrieval or processing.
        """
        return await self.repository.get_activities_by_trip()

    async def find_destinations_after_activity_start_time(self):
        """
        Retrieve all destinations that start after a specified time.

        This method delegates the query logic to the repository layer by calling
        `fetch_destinations_after()`. It is typically used to get upcoming or
        future destinations based on a time-based filter.

        Returns:
                list: A list of destination objects that start after the specified time.
        """
        return await self.repository.fetch_destinations_after_activity_start_time()

    async def activities_by_time_interval(self):
        """
        Retrieve all users who are participating in trips with an estimated budget
        above a specified minimum threshold.

        Returns:
            list[User]: A list of User instances meeting the budget criteria.
        """
        return await self.repository.activities_in_a_specified_interval()

    async def total_amount_of_payment_per_destination(self):
        """
        Calculate the total payment amount for all activities grouped by destination.

        This method calls the repository function `total_cost_of_activities_per_destination`,
        which aggregates the costs of all activities for each destination. The result can be
        used to display or analyze total expenses per destination.

        Returns:
            Any: The total payment amounts per destination, typically as a list of dictionaries
            or ORM result objects containing destination identifiers and the summed activity costs.
        """
        return await self.repository.total_cost_of_activities_per_destination()

    async def get_the_most_expensive_activity_per_destination(self):
        """
        Retrieve the most expensive activity for each destination.

        Returns:
            list[Activity]: A list of activities, where each entry represents the most
            expensive activity associated with a specific destination.
        """
        return await self.repository.most_expensive_activity_per_destination()

    async def fetch_users_in_trips_with_expensive_activities(self):
        """
        Retrieve all users who participated in trips that include destinations
        offering activities above a specified price threshold.

        Returns:
            list[User]:
                A list of users associated with trips containing at least one
                destination where an activity exceeds the defined price limit.
        """
        return await self.repository.get_users_in_trips_with_expensive_activities()

    async def get_most_expensive_trips(self):
        """
        Retrieve the most expensive trips based on their estimated budget.

        This method delegates the database query to the repository layer to fetch
        trips ordered by their estimated budget in descending order, returning
        those with the highest total cost.

        Returns:
            list[planner_schemas.MostExpensiveTrips]:
                A list of the most expensive trips, including details such as
                title, description, duration, and estimated budget.
        """
        return await self.repository.most_expensive_trips()

    async def trips_by_popularity(self):
        """
        Retrieve trips ordered by their popularity based on the number of participants.

        This method delegates the query to the repository layer, which counts the number
        of users participating in each trip and orders the trips in descending order
        of participant count.

        Returns:
            list[planner_schemas.TripPopularityOut]:
                A list of trips sorted by popularity, including trip details and the
                total number of participants for each trip.
        """
        return await self.repository.get_trips_by_popularity()

    async def destination_with_most_activities(self):
        """
        Retrieve destinations that have the highest number of activities.

        This method delegates the query to the repository layer, which counts the
        activities associated with each destination and returns them in descending
        order of activity count.

        Returns:
            list[planner_schemas.DestinationWithMostActivitiesSchemaOut]:
                A list of destinations, each including:
                - destination_id: The unique identifier of the destination.
                - name: The name of the destination.
                - activities_count: The total number of activities associated with the destination.
        """

        return await self.repository.get_destination_with_most_activities()

    async def get_average_price_of_activities_in_each_destination(self):
        """
        Calculate the average price of activities for each destination.

        This method delegates the query to the repository layer, which computes
        the mean price of all activities grouped by destination.

        Returns:
            list[planner_schemas.AverageActivityPricePerDestination]:
                A list where each item represents a destination and includes:
                - destination_id: The unique identifier of the destination.
                - destination_name: The name of the destination.
                - average_price: The average price of activities at that destination.
        """
        return await self.repository.average_price_of_activities_in_each_destination()
