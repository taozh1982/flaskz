"""Minimal itsdangerous compatibility layer used by jws.py."""

import base64
import hashlib
import hmac
import json
import string


class _CompactJSON:
    @staticmethod
    def loads(payload):
        return json.loads(payload)

    @staticmethod
    def dumps(obj, **kwargs):
        kwargs.setdefault("ensure_ascii", False)
        kwargs.setdefault("separators", (",", ":"))
        return json.dumps(obj, **kwargs)


class BadData(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


class BadSignature(BadData):
    def __init__(self, message, payload=None):
        super().__init__(message)
        self.payload = payload


class BadTimeSignature(BadSignature):
    def __init__(self, message, payload=None, date_signed=None):
        super().__init__(message, payload)
        self.date_signed = date_signed


class SignatureExpired(BadTimeSignature):
    pass


class BadHeader(BadSignature):
    def __init__(self, message, payload=None, header=None, original_error=None):
        super().__init__(message, payload)
        self.header = header
        self.original_error = original_error


class BadPayload(BadData):
    def __init__(self, message, original_error=None):
        super().__init__(message)
        self.original_error = original_error


def want_bytes(value, encoding="utf-8", errors="strict"):
    return value.encode(encoding, errors) if isinstance(value, str) else value


def base64_encode(value):
    return base64.urlsafe_b64encode(want_bytes(value)).rstrip(b"=")


def base64_decode(value):
    value = want_bytes(value, encoding="ascii", errors="ignore")
    value += b"=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(value)
    except (TypeError, ValueError) as e:
        raise BadData("Invalid base64-encoded data") from e


class SigningAlgorithm:
    def get_signature(self, key, value):
        raise NotImplementedError

    def verify_signature(self, key, value, sig):
        return hmac.compare_digest(sig, self.get_signature(key, value))


class NoneAlgorithm(SigningAlgorithm):
    def get_signature(self, key, value):
        return b""


class HMACAlgorithm(SigningAlgorithm):
    def __init__(self, digest_method=None):
        self.digest_method = hashlib.sha1 if digest_method is None else digest_method

    def get_signature(self, key, value):
        return hmac.new(key, msg=value, digestmod=self.digest_method).digest()


def _make_keys_list(secret_key):
    if isinstance(secret_key, (str, bytes)):
        secret_key = [secret_key]
    return [want_bytes(key) for key in secret_key]


_base64_alphabet = f"{string.ascii_letters}{string.digits}-_=".encode("ascii")


class Signer:
    default_digest_method = staticmethod(hashlib.sha1)
    default_key_derivation = "django-concat"

    def __init__(self, secret_key, salt=b"itsdangerous.Signer", sep=b".", key_derivation=None, digest_method=None, algorithm=None):
        self.secret_keys = _make_keys_list(secret_key)
        self.sep = want_bytes(sep)
        if self.sep in _base64_alphabet:
            raise ValueError(
                "The given separator cannot be used because it may be contained "
                "in the signature itself. ASCII letters, digits, and '-_=' must not be used."
            )

        self.salt = want_bytes(salt) if salt is not None else b"itsdangerous.Signer"
        self.key_derivation = self.default_key_derivation if key_derivation is None else key_derivation
        self.digest_method = self.default_digest_method if digest_method is None else digest_method
        self.algorithm = HMACAlgorithm(self.digest_method) if algorithm is None else algorithm

    @property
    def secret_key(self):
        return self.secret_keys[-1]

    def derive_key(self, secret_key=None):
        secret_key = self.secret_key if secret_key is None else want_bytes(secret_key)

        if self.key_derivation == "concat":
            return self.digest_method(self.salt + secret_key).digest()
        if self.key_derivation == "django-concat":
            return self.digest_method(self.salt + b"signer" + secret_key).digest()
        if self.key_derivation == "hmac":
            return hmac.new(secret_key, self.salt, self.digest_method).digest()
        if self.key_derivation == "none":
            return secret_key
        raise TypeError("Unknown key derivation method")

    def get_signature(self, value):
        value = want_bytes(value)
        return base64_encode(self.algorithm.get_signature(self.derive_key(), value))

    def sign(self, value):
        value = want_bytes(value)
        return value + self.sep + self.get_signature(value)

    def verify_signature(self, value, sig):
        try:
            sig = base64_decode(sig)
        except Exception:
            return False

        value = want_bytes(value)
        return any(
            self.algorithm.verify_signature(self.derive_key(key), value, sig)
            for key in reversed(self.secret_keys)
        )

    def unsign(self, signed_value):
        signed_value = want_bytes(signed_value)
        if self.sep not in signed_value:
            raise BadSignature(f"No {self.sep!r} found in value")

        value, sig = signed_value.rsplit(self.sep, 1)
        if self.verify_signature(value, sig):
            return value
        raise BadSignature(f"Signature {sig!r} does not match", payload=value)

    def validate(self, signed_value):
        try:
            self.unsign(signed_value)
            return True
        except BadSignature:
            return False


class Serializer:
    default_serializer = json
    default_signer = Signer

    def __init__(self, secret_key, salt=b"itsdangerous", serializer=None, serializer_kwargs=None, signer=None, signer_kwargs=None, fallback_signers=None):
        self.secret_keys = _make_keys_list(secret_key)
        self.salt = want_bytes(salt) if salt is not None else None
        self.serializer = self.default_serializer if serializer is None else serializer
        self.serializer_kwargs = {} if serializer_kwargs is None else serializer_kwargs
        self.signer = self.default_signer if signer is None else signer
        self.signer_kwargs = {} if signer_kwargs is None else signer_kwargs

    @property
    def secret_key(self):
        return self.secret_keys[-1]

    def load_payload(self, payload, serializer=None):
        if serializer is None:
            serializer = self.serializer
        try:
            if isinstance(serializer.dumps({}), str):
                payload = payload.decode("utf-8")
            return serializer.loads(payload)
        except Exception as e:
            raise BadPayload(
                "Could not load the payload because an exception occurred on unserializing the data.",
                original_error=e,
            ) from e

    def loads(self, s, salt=None, **kwargs):
        raise NotImplementedError()

    def _loads_unsafe_impl(self, s, salt, load_kwargs=None, load_payload_kwargs=None):
        try:
            return True, self.loads(s, salt=salt, **(load_kwargs or {}))
        except BadSignature as e:
            if e.payload is None:
                return False, None
            try:
                return False, self.load_payload(e.payload, **(load_payload_kwargs or {}))
            except BadPayload:
                return False, None
