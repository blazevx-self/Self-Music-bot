from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AccountData:
    id: int
    platform: str       # "vk" (потом добавим другие — parse_profile_link уже возвращает platform)
    screen_name: str    # "id2586505556" / "dlyanxs" — как в ссылке
    title: str          # отображаемое имя профиля/сообщества (для кнопки)
