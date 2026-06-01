"""Step definitions for authentication scenarios (Portuguese Gherkin)."""
import json
from behave import given, when, then

from app.models import User
from app.core.security import get_password_hash, create_access_token


@given('estou autenticado como "{email}" com senha "{password}"')
def step_authenticated_as(context, email, password):
    """Authenticate as a user and store the token in context."""
    # Login endpoint uses OAuth2PasswordRequestForm (form data, not JSON)
    response = context.client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200, \
        f"Authentication failed for {email}: {response.status_code} {response.text}"
    token_data = response.json()
    context.user_token = token_data["access_token"]
    # Set Authorization header on client for all subsequent requests
    context.client.headers["Authorization"] = f"Bearer {context.user_token}"


@then('a resposta deve conter um token de acesso válido')
def step_response_contains_valid_token(context):
    """Verify the response contains a valid access token."""
    data = context.response.json()
    assert "access_token" in data, f"Response does not contain access_token: {data}"
    assert len(data["access_token"]) > 0, "Access token is empty"
    context.user_token = data["access_token"]
    context.client.headers["Authorization"] = f"Bearer {context.user_token}"


@then('o papel do usuário no token deve ser "{expected_role}"')
def step_token_role(context, expected_role):
    """Verify the role claim in the JWT token."""
    from jose import jwt
    from app.core.config import get_settings

    token = context.user_token
    settings = get_settings()
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

    assert payload.get("role") == expected_role, \
        f"Expected role '{expected_role}', got '{payload.get('role')}'"


@when('eu envio uma requisição POST para "{endpoint}" com:')
def step_send_post_request_with_table(context, endpoint):
    """Send a POST request with table data (Portuguese) - colon variant for data tables."""
    data = {row['field']: row['value'] for row in context.table}
    endpoint = _resolve_endpoint(context, endpoint)
    data = _resolve_placeholders(context, data, endpoint=endpoint)

    headers = {}
    if hasattr(context, 'user_token') and context.user_token:
        headers['Authorization'] = f'Bearer {context.user_token}'

    # Auth login endpoint uses OAuth2PasswordRequestForm (form data, not JSON)
    if '/auth/login' in endpoint:
        context.response = context.client.post(endpoint, data=data, headers=headers)
        if context.response.status_code == 200:
            token_data = context.response.json()
            if "access_token" in token_data:
                context.user_token = token_data["access_token"]
                context.client.headers["Authorization"] = f"Bearer {context.user_token}"
    else:
        context.response = context.client.post(endpoint, json=data, headers=headers)


@when('eu envio uma requisição POST para "{endpoint}" com')
def step_send_post_request_pt(context, endpoint):
    """Send a POST request with table data (Portuguese) - no colon variant."""
    data = {row['field']: row['value'] for row in context.table}
    endpoint = _resolve_endpoint(context, endpoint)
    data = _resolve_placeholders(context, data, endpoint=endpoint)

    headers = {}
    if hasattr(context, 'user_token') and context.user_token:
        headers['Authorization'] = f'Bearer {context.user_token}'

    # Auth login endpoint uses OAuth2PasswordRequestForm (form data, not JSON)
    if '/auth/login' in endpoint:
        context.response = context.client.post(endpoint, data=data, headers=headers)
        if context.response.status_code == 200:
            token_data = context.response.json()
            if "access_token" in token_data:
                context.user_token = token_data["access_token"]
                context.client.headers["Authorization"] = f"Bearer {context.user_token}"
    else:
        context.response = context.client.post(endpoint, json=data, headers=headers)


@when('eu envio uma requisição GET para "{endpoint}"')
def step_send_get_request_pt(context, endpoint):
    """Send a GET request (Portuguese)."""
    # Resolve placeholders in endpoint URL
    endpoint = _resolve_endpoint(context, endpoint)

    headers = {}
    if hasattr(context, 'user_token') and context.user_token:
        headers['Authorization'] = f'Bearer {context.user_token}'

    context.response = context.client.get(endpoint, headers=headers)


@when('eu envio uma requisição PUT para "{endpoint}" com:')
def step_send_put_request_with_table(context, endpoint):
    """Send a PUT request with table data (Portuguese) - colon variant for data tables."""
    data = {row['field']: row['value'] for row in context.table}
    endpoint = _resolve_endpoint(context, endpoint)
    data = _resolve_placeholders(context, data, endpoint=endpoint)

    headers = {}
    if hasattr(context, 'user_token') and context.user_token:
        headers['Authorization'] = f'Bearer {context.user_token}'

    context.response = context.client.put(endpoint, json=data, headers=headers)


@when('eu envio uma requisição PUT para "{endpoint}" com')
def step_send_put_request_pt(context, endpoint):
    """Send a PUT request with table data (Portuguese) - no colon variant."""
    data = {row['field']: row['value'] for row in context.table}
    endpoint = _resolve_endpoint(context, endpoint)
    data = _resolve_placeholders(context, data, endpoint=endpoint)

    headers = {}
    if hasattr(context, 'user_token') and context.user_token:
        headers['Authorization'] = f'Bearer {context.user_token}'

    context.response = context.client.put(endpoint, json=data, headers=headers)


@when('eu envio uma requisição DELETE para "{endpoint}"')
def step_send_delete_request_pt(context, endpoint):
    """Send a DELETE request (Portuguese)."""
    # Resolve placeholders in endpoint URL
    endpoint = _resolve_endpoint(context, endpoint)

    headers = {}
    if hasattr(context, 'user_token') and context.user_token:
        headers['Authorization'] = f'Bearer {context.user_token}'

    context.response = context.client.delete(endpoint, headers=headers)


@then('o status da resposta deve ser {status_code:d}')
def step_response_status_pt(context, status_code):
    """Verify response status code (Portuguese)."""
    assert context.response.status_code == status_code, \
        f"Expected {status_code}, got {context.response.status_code}: {context.response.text}"


@then('a resposta deve conter "{field}" com valor "{expected_value}"')
def step_response_contains_field_pt(context, field, expected_value):
    """Verify a field in the response has the expected value (Portuguese)."""
    data = context.response.json()
    actual = data.get(field, f"<field '{field}' not found>")

    # Resolve placeholder in expected_value
    if expected_value.startswith('<') and expected_value.endswith('>'):
        placeholder = expected_value.strip('<>')
        expected_value = str(getattr(context, placeholder, expected_value))

    assert str(actual) == expected_value, \
        f"Expected '{field}' to be '{expected_value}', got '{actual}'"


@then('a resposta deve conter "{field}"')
def step_response_contains_field_exists_pt(context, field):
    """Verify a field exists in the response (Portuguese)."""
    data = context.response.json()
    assert field in data, f"Response does not contain field '{field}': {data}"


def _resolve_placeholders(context, data, endpoint=""):
    """Resolve <placeholder> values in request data from context attributes."""
    resolved = {}
    for key, value in data.items():
        if isinstance(value, str) and value.startswith('<') and value.endswith('>'):
            placeholder = value.strip('<>')
            resolved_value = getattr(context, placeholder, value)
            resolved[key] = str(resolved_value) if resolved_value != value else value
        else:
            resolved[key] = value
    # Map belt_id -> current_belt_id only for student API endpoints
    # (exams, belts, etc. use belt_id directly)
    if 'belt_id' in resolved and 'current_belt_id' not in resolved and '/students' in endpoint:
        resolved['current_belt_id'] = resolved.pop('belt_id')
    return resolved


def _resolve_endpoint(context, endpoint):
    """Resolve <placeholder> values in endpoint URLs from context attributes."""
    import re
    def replace_placeholder(match):
        placeholder = match.group(1)
        value = getattr(context, placeholder, match.group(0))
        return str(value)

    return re.sub(r'<(\w+)>', replace_placeholder, endpoint)