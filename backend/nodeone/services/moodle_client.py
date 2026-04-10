"""Cliente mínimo Moodle Web Services (REST form encoding). Sin lógica de negocio."""

from __future__ import annotations

import json
from typing import Any, List, Optional
from urllib.parse import urljoin

import requests


class MoodleClientError(Exception):
    pass


def _flatten(prefix: str, value: Any, out: List[tuple]) -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            _flatten(f'{prefix}[{k}]', v, out)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            _flatten(f'{prefix}[{i}]', item, out)
    else:
        if value is not None:
            out.append((prefix, value))


def _call(base_url: str, token: str, wsfunction: str, **params: Any) -> Any:
    base = (base_url or '').strip().rstrip('/')
    if not base or not token:
        raise MoodleClientError('Moodle base_url o token vacío')
    url = urljoin(base + '/', 'webservice/rest/server.php')
    flat: List[tuple] = [
        ('wstoken', token),
        ('wsfunction', wsfunction),
        ('moodlewsrestformat', 'json'),
    ]
    for key, val in params.items():
        if val is None:
            continue
        if isinstance(val, (list, dict)):
            _flatten(key, val, flat)
        else:
            flat.append((key, val))
    r = requests.post(url, data=flat, timeout=60)
    r.raise_for_status()
    try:
        data = r.json()
    except json.JSONDecodeError as e:
        raise MoodleClientError(f'Respuesta no JSON: {r.text[:200]}') from e
    if isinstance(data, dict) and data.get('exception'):
        raise MoodleClientError(
            f"{data.get('message', '')} ({data.get('errorcode', '')})"
        )
    return data


def get_user_by_email(base_url: str, token: str, email: str) -> Optional[dict]:
    email = (email or '').strip().lower()
    if not email:
        return None
    try:
        users = _call(base_url, token, 'core_user_get_users_by_field', field='email', values=[email])
    except MoodleClientError:
        return None
    if isinstance(users, list) and users:
        return users[0]
    return None


def create_user(
    base_url: str,
    token: str,
    *,
    username: str,
    email: str,
    firstname: str,
    lastname: str,
    password: str,
) -> int:
    users = _call(
        base_url,
        token,
        'core_user_create_users',
        users=[
            {
                'username': username[:100],
                'createpassword': 0,
                'firstname': firstname[:100] or 'User',
                'lastname': lastname[:100] or 'NodeOne',
                'email': email[:100],
                'password': password,
            }
        ],
    )
    if isinstance(users, list) and users and users[0].get('id'):
        return int(users[0]['id'])
    raise MoodleClientError('core_user_create_users sin id')


def ensure_moodle_user(
    base_url: str,
    token: str,
    *,
    email: str,
    firstname: str,
    lastname: str,
) -> int:
    import secrets
    import string

    existing = get_user_by_email(base_url, token, email)
    if existing and existing.get('id'):
        return int(existing['id'])
    local = (email.split('@')[0] if '@' in email else email).replace('.', '_')[:20]
    username = f'n1_{local}_{secrets.token_hex(3)}'
    alphabet = string.ascii_letters + string.digits
    pwd = ''.join(secrets.choice(alphabet) for _ in range(20))
    return create_user(
        base_url,
        token,
        username=username,
        email=email,
        firstname=firstname,
        lastname=lastname,
        password=pwd,
    )


def create_course(
    base_url: str,
    token: str,
    *,
    fullname: str,
    shortname: str,
    categoryid: int = 1,
) -> int:
    courses = _call(
        base_url,
        token,
        'core_course_create_courses',
        courses=[
            {
                'fullname': fullname[:254],
                'shortname': shortname[:100],
                'categoryid': int(categoryid),
            }
        ],
    )
    if isinstance(courses, list) and courses and courses[0].get('id'):
        return int(courses[0]['id'])
    raise MoodleClientError('core_course_create_courses sin id')


def enrol_manual(
    base_url: str,
    token: str,
    *, roleid: int, userid: int, courseid: int
) -> None:
    _call(
        base_url,
        token,
        'enrol_manual_enrol_users',
        enrolments=[{'roleid': roleid, 'userid': userid, 'courseid': courseid}],
    )


def unenrol_manual(
    base_url: str,
    token: str,
    *, userid: int, courseid: int
) -> None:
    _call(
        base_url,
        token,
        'enrol_manual_unenrol_users',
        enrolments=[{'userid': userid, 'courseid': courseid}],
    )
