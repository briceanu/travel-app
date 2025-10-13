from abc import ABC, abstractmethod


class AbstractAdminInterface(ABC):

    @abstractmethod
    def remove_user(self):
        pass

    @abstractmethod
    def update_user_is_active_status(self):
        pass

    @abstractmethod
    def get_planners_and_users(self):
        pass
