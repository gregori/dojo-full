from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Event, EventType, PreCheckIn
from app.schemas import EventCreate, EventTypeCreate, EventTypeUpdate, EventUpdate


class EventTypeService:
    @staticmethod
    def get_event_type(db: Session, event_type_id: str) -> EventType | None:
        return db.query(EventType).filter(EventType.id == event_type_id).first()

    @staticmethod
    def get_event_types(db: Session, skip: int = 0, limit: int = 100) -> list[EventType]:
        return db.query(EventType).offset(skip).limit(limit).all()

    @staticmethod
    def create_event_type(db: Session, event_type_data: EventTypeCreate) -> EventType:
        db_type = EventType(**event_type_data.model_dump())
        db.add(db_type)
        db.commit()
        db.refresh(db_type)
        return db_type

    @staticmethod
    def update_event_type(db: Session, event_type_id: str, event_type_data: EventTypeUpdate) -> EventType:
        event_type = EventTypeService.get_event_type(db, event_type_id)
        if not event_type:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event type not found")

        update_data = event_type_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(event_type, field, value)

        db.commit()
        db.refresh(event_type)
        return event_type

    @staticmethod
    def delete_event_type(db: Session, event_type_id: str) -> None:
        event_type = EventTypeService.get_event_type(db, event_type_id)
        if not event_type:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event type not found")
        db.delete(event_type)
        db.commit()


class EventService:
    @staticmethod
    def get_event(db: Session, event_id: str) -> Event | None:
        return db.query(Event).filter(Event.id == event_id).first()

    @staticmethod
    def get_event_by_token(db: Session, token: str) -> Event | None:
        return db.query(Event).filter(Event.check_in_token == token).first()

    @staticmethod
    def get_events(
        db: Session, status: str | None = None, event_type_id: str | None = None, skip: int = 0, limit: int = 100
    ) -> list[Event]:
        query = db.query(Event)
        if status:
            query = query.filter(Event.status == status)
        if event_type_id:
            query = query.filter(Event.event_type_id == event_type_id)
        return query.order_by(Event.start_datetime.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def create_event(db: Session, event_data: EventCreate, created_by: str) -> Event:
        db_event = Event(
            **event_data.model_dump(),
            created_by=created_by,
            status="scheduled",
        )
        db.add(db_event)
        db.commit()
        db.refresh(db_event)
        return db_event

    @staticmethod
    def cancel_pre_checkins_for_event(db: Session, event: Event) -> None:
        """Cancel every confirmed PreCheckIn for an event, setting cancelled_at.

        Extracted from update_event's existing reschedule-cutoff cascade (the
        loop body below is unchanged, just given a name and a second caller) so
        every path that cancels an Event -- this service's own delete_event
        (RES-09's actual bug fix), update_event's pre-existing reschedule-cutoff
        trigger, and EventSeriesService's Case B / deactivation cascade -- shares
        one implementation instead of three copies of the same loop.
        """
        now = datetime.now(UTC)
        for pre_checkin in (
            db.query(PreCheckIn).filter(PreCheckIn.event_id == event.id, PreCheckIn.status == "confirmed").all()
        ):
            pre_checkin.status = "cancelled"
            pre_checkin.cancelled_at = now

    @staticmethod
    def update_event(db: Session, event_id: str, event_data: EventUpdate) -> Event:
        event = EventService.get_event(db, event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

        update_data = event_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(event, field, value)

        # A reschedule into the one-hour cutoff invalidates existing intent;
        # attendees must explicitly confirm again once the event is reopened.
        if "start_datetime" in update_data:
            start_datetime = event.start_datetime
            if start_datetime.tzinfo is None:
                start_datetime = start_datetime.replace(tzinfo=UTC)
            if start_datetime <= datetime.now(UTC) + timedelta(hours=1):
                EventService.cancel_pre_checkins_for_event(db, event)

        event.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(event)
        return event

    @staticmethod
    def delete_event(db: Session, event_id: str) -> None:
        """RES-09 fix: cancelling an Event now also cascades to its confirmed
        PreCheckIns -- this was the pre-existing gap (this method previously
        only set event.status, never touching PreCheckIn).
        """
        event = EventService.get_event(db, event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
        event.status = "cancelled"
        event.updated_at = datetime.now(UTC)
        EventService.cancel_pre_checkins_for_event(db, event)
        db.commit()
