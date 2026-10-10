from enum import Enum


class TreeSuggestionMode(str, Enum):
    CREATE = 'create'
    ENRICH = 'enrich'


class TreeSuggestionStatus(str, Enum):
    PROCESSING = 'processing'
    READY = 'ready'
    FAILED = 'failed'
    COMPLETED = 'completed'


class TreeSuggestionItemKind(str, Enum):
    SOURCE = 'source'
    TYPIFICATION = 'typification'
    TAXONOMY = 'taxonomy'
    BRANCH = 'branch'


class TreeSuggestionItemOperation(str, Enum):
    CREATE = 'create'
    UPDATE = 'update'


class TreeSuggestionItemStatus(str, Enum):
    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    DISCARDED = 'discarded'
