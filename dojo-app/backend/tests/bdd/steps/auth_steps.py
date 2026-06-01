"""Step definitions for authentication scenarios (Portuguese Gherkin)."""
import json
from behave import given, when, then

from app.models import User
from app.core.security import get_password_hash, create_access_token


@given('estou autenticado como "{email}" com senha "{password}"')
def step_authenticated_as(context, email, password):
    """Authenticate as a user and store the token in context."""
    import requests
    url = context.base_url + "/api/v1/auth/login"
    data = {"username": email, "password": password}
    response = requests.post(url, data=data)
    assert response.status_code == 200, \
        f"Authentication failed for {email}: {response.status_code} {response.text}"
    token_data = response.json()
    context.user_token = token_data["access_token"]


@then('a resposta deve conter um token de acesso válido')
def step_response_contains_valid_token(context):
    """Verify the response contains a valid access token."""
    data = context.response.json()
    assert "access_token" in data, f"Response does not contain access_token: {data}"
    assert len(data["access_token"]) > 0, "Access token is empty"
    context.user_token = data["access_token"]


@then('o papel do usuário no token deve ser "{expected_role}"')
def step_token_role(context, expected_role):
    """Verify the role claim in the JWT token."""
    import jwt
    from app.core.config import get_settings

    token = context.user_token
    settings = get_settings()
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

    assert payload.get("role") == expected_role, \
        f"Expected role '{expected_role}', got '{payload.get('role')}'"


@when('eu envio uma requisição POST para "{endpoint}" com')
def step_send_post_request_pt(context, endpoint):
    """Send a POST request with table data (Portuguese)."""
    import requests
    data = {row['field']: row['value'] for row in context.table}

    # Resolve placeholders from context
    data = _resolve_placeholders(context, data)

    url = context.base_url + endpoint
    headers = {}
    if hasattr(context, 'user_token') and context.user_token:
        headers['Authorization'] = f'Bearer {context.user_token}'

    context.response = requests.post(url, json=data, headers=headers)


@when('eu envio uma requisição GET para "{endpoint}"')
def step_send_get_request_pt(context, endpoint):
    """Send a GET request (Portuguese)."""
    import requests
    url = context.base_url + endpoint
    headers = {}
    if hasattr(context, 'user_token') and context.user_token:
        headers['Authorization'] = f'Bearer {context.user_token}'

    context.response = requests.get(url, headers=headers)


@when('eu envio uma requisição PUT para "{endpoint}" com')
def step_send_put_request_pt(context, endpoint):
    """Send a PUT request with table data (Portuguese)."""
    import requests
    data = {row['field']: row['value'] for row in context.table}

    # Resolve placeholders from context
    data = _resolve_placeholders(context, data)

    url = context.base_url + endpoint
    headers = {}
    if hasattr(context, 'user_token') and context.user_token:
        headers['Authorization'] = f'Bearer {context.user_token}'

    context.response = requests.put(url, json=data, headers=headers)


@when('eu envio uma requisição DELETE para "{endpoint}"')
def step_send_delete_request_pt(context, endpoint):
    """Send a DELETE request (Portuguese)."""
    import requests
    url = context.base_url + endpoint
    headers = {}
    if hasattr(context, 'user_token') and context.user_token:
        headers['Authorization'] = f'Bearer {context.user_token}'

    context.response = requests.delete(url, headers=headers)


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


def _resolve_placeholders(context, data):
    """Resolve <placeholder> values in request data from context attributes."""
    resolved = {}
    for key, value in data.items():
        if isinstance(value, str) and value.startswith('<') and value.endswith('>'):
            placeholder = value.strip('<>')
            resolved_value = getattr(context, placeholder, value)
            resolved[key] = str(resolved_value) if resolved_value != value else value
        else:
            resolved[key] = value
    return resolved