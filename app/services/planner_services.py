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
