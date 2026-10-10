from datetime import datetime
from uuid import uuid4

from lumina.models import TreeSuggestionItem, TreeSuggestionSession
from lumina.schemas import (
    TreeSuggestionItemKind,
    TreeSuggestionSessionDetail,
    TreeSuggestionStatus,
)


def test_session_detail_from_orm():
    suggestion_session = TreeSuggestionSession(
        mode='create',
        file_path='/uploads/norma.pdf',
        original_filename='norma.pdf',
        excluded_rules=[
            {
                'title': 'Fonte Arial 12',
                'quote': 'O texto deve ser digitado em fonte Arial',
                'pages': [2],
            }
        ],
    )
    suggestion_session.created_at = datetime.now()
    item = TreeSuggestionItem(
        session_id=suggestion_session.id,
        kind='branch',
        operation='create',
        proposed_title='Resumo com até 500 palavras',
        position=0,
        evidence=[{'quote': 'O resumo terá até 500 palavras', 'pages': [3]}],
        parent_entity_id=uuid4(),
    )
    suggestion_session.items.append(item)

    detail = TreeSuggestionSessionDetail.model_validate(suggestion_session)

    assert detail.status == TreeSuggestionStatus.PROCESSING
    assert detail.items[0].kind == TreeSuggestionItemKind.BRANCH
    assert detail.items[0].evidence[0].pages == [3]
    assert detail.items[0].parent_entity_title is None
    assert detail.excluded_rules[0].title == 'Fonte Arial 12'
    assert detail.excluded_rules[0].pages == [2]
