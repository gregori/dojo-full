"""Step definitions for event management scenarios (Portuguese Gherkin)."""
from behave import given, when, then

from app.models import Event


@given('o evento "{title}" foi cancelado')
def step_event_cancelled(context, title):
    """Cancel an event by setting its status to 'cancelled'."""
    db = context.db
    event = context.events.get(title) if hasattr(context, 'events') else None
    if event is None:
        event = context.current_event
    assert event is not None, f"Event '{title}' not found in context"
    event.status = "cancelled"
    db.commit()


@then('a resposta deve conter uma lista de eventos')
def step_response_contains_event_list(context):
    """Verify the response is a list of events."""
    data = context.response.json()
    assert isinstance(data, list), f"Expected a list, got {type(data)}"


@then('o token do QR Code deve ser válido')
def step_qr_code_token_valid(context):
    """Verify the QR code token is present and valid."""
    data = context.response.json()
    assert "check_in_token" in data, f"Response does not contain check_in_token: {data}"
    token = data["check_in_token"]
    assert len(token) > 0, "QR code token is empty"