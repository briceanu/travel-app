from abc import ABC, abstractmethod


class AbstractUserInterface(ABC):

    @abstractmethod
    def create_user(self) -> None:
        pass

    @abstractmethod
    def login_user(self) -> None:
        pass

    @abstractmethod
    def logout_user(self) -> None:
        pass

    @abstractmethod
    def access_token_from_refresh_token(self) -> None:
        pass

    @abstractmethod
    def update_user_name(self) -> None:
        pass

    @abstractmethod
    def update_user_password(self) -> None:
        pass

    @abstractmethod
    def update_user_email(self) -> None:
        pass

    @abstractmethod
    def update_user_phone_number(self) -> None:
        pass

    @abstractmethod
    def update_date_of_birth(self) -> None:
        pass

    @abstractmethod
    def update_profile_picture(self) -> None:
        pass

    @abstractmethod
    def delete_profile_picture(self) -> None:
        pass

    @abstractmethod
    def get_user_profile(self) -> None:
        pass

    @abstractmethod
    def get_user_profile_image(self) -> None:
        pass

    @abstractmethod
    def deactivate_user_account(self) -> None:
        pass

    @abstractmethod
    def reactivate_user_account(self) -> None:
        pass

    @abstractmethod
    def register_for_trip(self) -> None:
        pass

    @abstractmethod
    def unregister_from_trip(self) -> None:
        pass
