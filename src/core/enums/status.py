from enum import StrEnum

class ResultStatus(StrEnum):
    SUCCESS = "SUCCESS"
    NEED_SUBSCRIBE = "NEED_SUBSCRIBE"
    NOT_SUBSCRIBED = "NOT_SUBSCRIBE"