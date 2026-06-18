import pytest
from jose import JWTError
from security.jwt import hash_password, verify_password, create_access_token, decode_token


def test_password_hash_roundtrip() -> None:
    h = hash_password("s3cret!")
    assert h != "s3cret!"
    assert verify_password("s3cret!", h) is True
    assert verify_password("wrong", h) is False


def test_access_token_encodes_subject() -> None:
    token = create_access_token("user-123")
    claims = decode_token(token)
    assert claims["sub"] == "user-123"
    assert claims["type"] == "access"


def test_decode_rejects_garbage() -> None:
    with pytest.raises(JWTError):
        decode_token("not-a-jwt")
