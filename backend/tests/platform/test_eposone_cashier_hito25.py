from nodeone.modules.eposone.cashier_service import _build_pin_verifier, verify_pin


def test_pin_verifier_is_salted_and_never_contains_plain_pin():
    first = _build_pin_verifier('1234')
    second = _build_pin_verifier('1234')

    assert first != second
    assert '1234' not in first
    assert first.startswith('pbkdf2_sha256$310000$')
    assert verify_pin('1234', first)
    assert not verify_pin('4321', first)


def test_pin_verifier_rejects_invalid_pin_and_malformed_verifier():
    try:
        _build_pin_verifier('12ab')
    except ValueError as exc:
        assert '4 y 8 dígitos' in str(exc)
    else:
        raise AssertionError('Se esperaba PIN inválido')

    assert not verify_pin('1234', 'malformed')
