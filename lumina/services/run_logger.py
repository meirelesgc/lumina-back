import json
import re
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import aiofiles

from lumina.core.settings import Settings
from lumina.schemas.processing_run import (
    CriterionEvaluationRecord,
    ProcessingEvent,
    ProcessingEventType,
    ProcessingRunDetail,
    ProcessingRunListResponse,
    ProcessingRunSummary,
    ProcessingStageDetail,
    ProcessingStatus,
)

SETTINGS = Settings()

CPF_PATTERN = re.compile(r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b')
CNPJ_PATTERN = re.compile(r'\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b')
PHONE_PATTERN = re.compile(
    r'\b(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?\d{4,5}-?\d{4}\b'
)
EMAIL_PATTERN = re.compile(
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
)
UUID_PATTERN = re.compile(
    r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b'
)
ID_KEYS = {
    'id',
    'run_id',
    'release_id',
    'document_id',
    'project_id',
    'user_id',
    'stage_id',
    'criterion_id',
}


def sanitize_pii(text: str) -> str:
    if not isinstance(text, str):
        return text

    uuids: List[str] = []

    def _replace_uuid(match: re.Match[str]) -> str:
        idx = len(uuids)
        uuids.append(match.group(0))
        return f'__UUID_TOKEN_{idx}__'

    protected_text = UUID_PATTERN.sub(_replace_uuid, text)

    protected_text = CPF_PATTERN.sub('[CPF_MASKED]', protected_text)
    protected_text = CNPJ_PATTERN.sub('[CNPJ_MASKED]', protected_text)
    protected_text = PHONE_PATTERN.sub('[PHONE_MASKED]', protected_text)
    protected_text = EMAIL_PATTERN.sub('[EMAIL_MASKED]', protected_text)

    for idx, original_uuid in enumerate(uuids):
        protected_text = protected_text.replace(
            f'__UUID_TOKEN_{idx}__', original_uuid
        )

    return protected_text


def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    sanitized: Dict[str, Any] = {}
    for key, val in data.items():
        if key in ID_KEYS or key.endswith('_id'):
            sanitized[key] = val
        elif isinstance(val, str):
            sanitized[key] = sanitize_pii(val)
        elif isinstance(val, dict):
            sanitized[key] = sanitize_dict(val)
        elif isinstance(val, list):
            sanitized[key] = [
                sanitize_dict(item)
                if isinstance(item, dict)
                else sanitize_pii(item)
                if isinstance(item, str)
                else item
                for item in val
            ]
        else:
            sanitized[key] = val
    return sanitized


def _build_stage_detail(
    stage_name: str, s_events: List[ProcessingEvent]
) -> ProcessingStageDetail:
    s_started_at = s_events[0].timestamp
    s_finished_at: Optional[datetime] = None
    s_status = ProcessingStatus.IN_PROGRESS
    s_duration_ms: Optional[int] = None
    s_item_count: Optional[int] = None
    s_error: Optional[str] = None
    s_items: List[Dict[str, Any]] = []
    s_meta: Dict[str, Any] = {}

    for s_ev in s_events:
        if s_ev.event == ProcessingEventType.CRITERION_EVALUATED.value:
            if s_ev.data:
                s_items.append(s_ev.data)
        elif s_ev.event == ProcessingEventType.STAGE_PROGRESS.value:
            if s_ev.item_count is not None:
                s_item_count = s_ev.item_count
        elif s_ev.event == ProcessingEventType.STAGE_COMPLETED.value:
            s_status = ProcessingStatus.COMPLETED
            s_finished_at = s_ev.timestamp
            s_duration_ms = s_ev.duration_ms
            if s_ev.item_count is not None:
                s_item_count = s_ev.item_count
            if s_ev.data:
                s_meta.update(s_ev.data)
        elif s_ev.event == ProcessingEventType.STAGE_FAILED.value:
            s_status = ProcessingStatus.FAILED
            s_finished_at = s_ev.timestamp
            s_duration_ms = s_ev.duration_ms
            s_error = s_ev.error

    if not s_duration_ms and s_finished_at:
        diff = (s_finished_at - s_started_at).total_seconds()
        s_duration_ms = int(diff * 1000)
    if not s_item_count and s_items:
        s_item_count = len(s_items)

    return ProcessingStageDetail(
        name=stage_name,
        status=s_status,
        started_at=s_started_at,
        finished_at=s_finished_at,
        duration_ms=s_duration_ms,
        item_count=s_item_count,
        error_details=s_error,
        items=s_items,
        metadata=s_meta,
    )


class RunLogger:
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = Path(base_dir or SETTINGS.PIPELINE_RUNS_DIRECTORY)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.base_dir / 'index.jsonl'

    def _get_run_file(self, run_id: UUID) -> Path:
        return self.base_dir / f'{run_id}.jsonl'

    async def append_event(self, event: ProcessingEvent) -> None:
        if event.error:
            event.error = sanitize_pii(event.error)
        if event.data:
            event.data = sanitize_dict(event.data)

        run_file = self._get_run_file(event.run_id)
        serialized_line = event.model_dump_json() + '\n'

        async with aiofiles.open(run_file, mode='a', encoding='utf-8') as f:
            await f.write(serialized_line)

        if event.event in {
            ProcessingEventType.RUN_STARTED.value,
            ProcessingEventType.RUN_COMPLETED.value,
            ProcessingEventType.RUN_FAILED.value,
        }:
            await self._update_index(event)

    async def _update_index(self, event: ProcessingEvent) -> None:
        run_detail = await self.get_run_detail(event.run_id)
        if not run_detail:
            return

        summary = ProcessingRunSummary(
            id=run_detail.id,
            release_id=run_detail.release_id,
            document_id=run_detail.document_id,
            document_name=run_detail.document_name,
            status=run_detail.status,
            started_at=run_detail.started_at,
            finished_at=run_detail.finished_at,
            duration_ms=run_detail.duration_ms,
            stages_count=len(run_detail.stages),
            error_summary=run_detail.error_summary,
        )

        entries: Dict[str, str] = {}
        if self.index_file.exists():
            async with aiofiles.open(
                self.index_file, mode='r', encoding='utf-8'
            ) as f:
                async for line in f:
                    line_str = line.strip()
                    if not line_str:
                        continue
                    try:
                        raw = json.loads(line_str)
                        r_id = raw.get('id') or raw.get('run_id')
                        if r_id:
                            entries[str(r_id)] = line_str
                    except Exception:
                        continue

        entries[str(summary.id)] = summary.model_dump_json()

        async with aiofiles.open(
            self.index_file, mode='w', encoding='utf-8'
        ) as f:
            for line_val in entries.values():
                await f.write(line_val + '\n')

    async def start_run(
        self,
        run_id: UUID,
        document_id: UUID,
        document_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProcessingEvent:
        event = ProcessingEvent(
            run_id=run_id,
            event=ProcessingEventType.RUN_STARTED.value,
            status=ProcessingStatus.IN_PROGRESS,
            data={
                'document_id': str(document_id),
                'document_name': document_name,
                **(metadata or {}),
            },
        )
        await self.append_event(event)
        return event

    async def start_stage(
        self,
        run_id: UUID,
        stage: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProcessingEvent:
        event = ProcessingEvent(
            run_id=run_id,
            event=ProcessingEventType.STAGE_STARTED.value,
            stage=stage,
            status=ProcessingStatus.IN_PROGRESS,
            data=metadata or {},
        )
        await self.append_event(event)
        return event

    async def progress_stage(
        self,
        run_id: UUID,
        stage: str,
        item_count: Optional[int] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> ProcessingEvent:
        event = ProcessingEvent(
            run_id=run_id,
            event=ProcessingEventType.STAGE_PROGRESS.value,
            stage=stage,
            status=ProcessingStatus.IN_PROGRESS,
            item_count=item_count,
            data=data or {},
        )
        await self.append_event(event)
        return event

    async def record_criterion(
        self,
        run_id: UUID,
        stage: str,
        criterion_record: CriterionEvaluationRecord,
    ) -> ProcessingEvent:
        data = criterion_record.model_dump()
        event = ProcessingEvent(
            run_id=run_id,
            event=ProcessingEventType.CRITERION_EVALUATED.value,
            stage=stage,
            status=criterion_record.status,
            duration_ms=criterion_record.duration_ms,
            error=criterion_record.error_message,
            data=data,
        )
        await self.append_event(event)
        return event

    async def complete_stage(
        self,
        run_id: UUID,
        stage: str,
        duration_ms: Optional[int] = None,
        item_count: Optional[int] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> ProcessingEvent:
        event = ProcessingEvent(
            run_id=run_id,
            event=ProcessingEventType.STAGE_COMPLETED.value,
            stage=stage,
            status=ProcessingStatus.COMPLETED,
            duration_ms=duration_ms,
            item_count=item_count,
            data=data or {},
        )
        await self.append_event(event)
        return event

    async def fail_stage(
        self,
        run_id: UUID,
        stage: str,
        error: str,
        duration_ms: Optional[int] = None,
    ) -> ProcessingEvent:
        event = ProcessingEvent(
            run_id=run_id,
            event=ProcessingEventType.STAGE_FAILED.value,
            stage=stage,
            status=ProcessingStatus.FAILED,
            duration_ms=duration_ms,
            error=error,
        )
        await self.append_event(event)
        return event

    async def _read_index_summaries(self) -> List[ProcessingRunSummary]:
        if not self.index_file.exists():
            return []
        summaries: List[ProcessingRunSummary] = []
        async with aiofiles.open(
            self.index_file, mode='r', encoding='utf-8'
        ) as f:
            async for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    summary = ProcessingRunSummary.model_validate_json(
                        line_str
                    )
                    summaries.append(summary)
                except Exception:
                    continue
        return summaries

    async def purge_old_runs(
        self, max_runs: int = 30, max_age_days: int = 7
    ) -> int:
        summaries = await self._read_index_summaries()
        if not summaries:
            return 0

        now = datetime.now(timezone.utc)
        cutoff_date = now - timedelta(days=max_age_days)
        summaries.sort(key=lambda s: s.started_at, reverse=True)

        retained: List[ProcessingRunSummary] = []
        purged_ids: List[UUID] = []

        for idx, summary in enumerate(summaries):
            s_date = summary.started_at
            if s_date.tzinfo is None:
                s_date = s_date.replace(tzinfo=timezone.utc)

            if idx < max_runs and s_date >= cutoff_date:
                retained.append(summary)
            else:
                purged_ids.append(summary.id)

        for p_id in purged_ids:
            run_file = self._get_run_file(p_id)
            if run_file.exists():
                try:
                    run_file.unlink(missing_ok=True)
                except OSError:
                    pass

        async with aiofiles.open(
            self.index_file, mode='w', encoding='utf-8'
        ) as f:
            for summary in retained:
                await f.write(summary.model_dump_json() + '\n')

        return len(purged_ids)

    async def complete_run(
        self,
        run_id: UUID,
        duration_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProcessingEvent:
        event = ProcessingEvent(
            run_id=run_id,
            event=ProcessingEventType.RUN_COMPLETED.value,
            status=ProcessingStatus.COMPLETED,
            duration_ms=duration_ms,
            data=metadata or {},
        )
        await self.append_event(event)
        try:
            await self.purge_old_runs()
        except Exception:
            pass
        return event

    async def fail_run(
        self,
        run_id: UUID,
        error: str,
        duration_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProcessingEvent:
        event = ProcessingEvent(
            run_id=run_id,
            event=ProcessingEventType.RUN_FAILED.value,
            status=ProcessingStatus.FAILED,
            duration_ms=duration_ms,
            error=error,
            data=metadata or {},
        )
        await self.append_event(event)
        try:
            await self.purge_old_runs()
        except Exception:
            pass
        return event

    async def get_run_events(self, run_id: UUID) -> List[ProcessingEvent]:
        run_file = self._get_run_file(run_id)
        if not run_file.exists():
            return []

        events: List[ProcessingEvent] = []
        async with aiofiles.open(run_file, mode='r', encoding='utf-8') as f:
            async for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    events.append(
                        ProcessingEvent.model_validate_json(line_str)
                    )
                except Exception:
                    continue
        return events

    @staticmethod
    def _parse_run_events(
        events: List[ProcessingEvent],
    ) -> Tuple[
        ProcessingStatus,
        Optional[datetime],
        Optional[int],
        Optional[str],
        Dict[str, Any],
        List[str],
        Dict[str, List[ProcessingEvent]],
    ]:
        status = ProcessingStatus.IN_PROGRESS
        finished_at: Optional[datetime] = None
        duration_ms: Optional[int] = None
        error_summary: Optional[str] = None
        top_metadata: Dict[str, Any] = {}
        stage_names_order: List[str] = []
        stage_events_map: Dict[str, List[ProcessingEvent]] = {}

        for ev in events:
            if ev.data:
                top_metadata.update(ev.data)
            if ev.event == ProcessingEventType.RUN_COMPLETED.value:
                status = ProcessingStatus.COMPLETED
                finished_at = ev.timestamp
                duration_ms = ev.duration_ms
            elif ev.event == ProcessingEventType.RUN_FAILED.value:
                status = ProcessingStatus.FAILED
                finished_at = ev.timestamp
                duration_ms = ev.duration_ms
                error_summary = ev.error

            if ev.stage:
                if ev.stage not in stage_events_map:
                    stage_names_order.append(ev.stage)
                    stage_events_map[ev.stage] = []
                stage_events_map[ev.stage].append(ev)

        return (
            status,
            finished_at,
            duration_ms,
            error_summary,
            top_metadata,
            stage_names_order,
            stage_events_map,
        )

    async def get_run_detail(
        self, run_id: UUID
    ) -> Optional[ProcessingRunDetail]:
        events = await self.get_run_events(run_id)
        if not events:
            return None

        first_event = events[0]
        document_id_str = first_event.data.get('document_id')
        doc_id = UUID(document_id_str) if document_id_str else UUID(int=0)
        doc_name = first_event.data.get('document_name')
        started_at = first_event.timestamp

        (
            status,
            finished_at,
            duration_ms,
            error_summary,
            top_metadata,
            stage_names_order,
            stage_events_map,
        ) = self._parse_run_events(events)

        if not duration_ms and finished_at:
            diff = (finished_at - started_at).total_seconds()
            duration_ms = int(diff * 1000)

        stages = [
            _build_stage_detail(name, stage_events_map[name])
            for name in stage_names_order
        ]

        return ProcessingRunDetail(
            id=run_id,
            release_id=run_id,
            document_id=doc_id,
            document_name=doc_name,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            error_summary=error_summary,
            stages=stages,
            metadata=top_metadata,
        )

    async def list_runs(
        self,
        limit: int = 20,
        offset: int = 0,
        status: Optional[ProcessingStatus] = None,
        release_id: Optional[UUID] = None,
        document_id: Optional[UUID] = None,
    ) -> ProcessingRunListResponse:
        all_summaries = await self._read_index_summaries()
        all_summaries.sort(key=lambda s: s.started_at, reverse=True)

        filtered = all_summaries
        if status:
            filtered = [s for s in filtered if s.status == status]
        if release_id:
            filtered = [s for s in filtered if s.release_id == release_id]
        if document_id:
            filtered = [s for s in filtered if s.document_id == document_id]

        total = len(filtered)
        paginated = filtered[offset : offset + limit]

        return ProcessingRunListResponse(
            items=paginated,
            total=total,
            limit=limit,
            offset=offset,
        )


@lru_cache
def get_run_logger() -> RunLogger:
    return RunLogger()
