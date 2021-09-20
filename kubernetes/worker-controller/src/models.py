from typing import TypedDict, List, Dict


class SocketQueueEntry(TypedDict):
    """
    Type describing the used parts of the queue info
    """
    name: str
    pending_count: int
    worker_count: int
    queued_count: int
    running_count: int


class QueueStatusTask(TypedDict):
    queue_name: str


class QueueStatusAnalysis(TypedDict):
    id: int
    lookup_chunks: int
    analysis_chunks: int
    sub_task_count: int
    sub_task_statuses: List[QueueStatusTask]


class QueueStatusAnalysesEntry(TypedDict):
    analysis: List[QueueStatusAnalysis]


class QueueStatusContentEntry(TypedDict):
    """
    Type describing the used parts of an entry in the web socket message
    """
    queue: SocketQueueEntry
    analyses: List[QueueStatusAnalysesEntry]


class QueueStatusSocketMessage(TypedDict):
    """
    Type describing the used parts of the socket message
    """
    content: List[QueueStatusContentEntry]

# TODO

class RunningAnalysis(TypedDict):
    id: int
    tasks: int
    queue_names: List[str]


class ModelState(TypedDict):
    tasks: int
    analyses: int
