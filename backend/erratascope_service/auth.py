"""JWT verification against a local public JWKS or a hosted HTTPS JWKS."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

import httpx
import jwt
from jwt.algorithms import RSAAlgorithm, ECAlgorithm

from .config import Settings
from .errors import ApiError

MAX_JWKS_BYTES = 1024 * 1024
HOSTED_CACHE_SECONDS = 600


class TokenError(Exception):
    pass


def _key_from_jwk(jwk: dict[str, Any], algorithms: tuple[str, ...]):
    key_type = jwk.get("kty")
    if key_type == "RSA":
        return RSAAlgorithm.from_jwk(jwk)
    if key_type == "EC":
        return ECAlgorithm.from_jwk(jwk)
    raise TokenError("unsupported JWK key type")


class LocalJWKS:
    def __init__(self, path: Path, algorithms: tuple[str, ...]) -> None:
        self.path = path
        self.algorithms = algorithms
        self._keys: dict[str, Any] | None = None
        self._mtime: float | None = None

    def _load(self) -> dict[str, Any]:
        stat = self.path.stat()
        if self._keys is None or self._mtime != stat.st_mtime:
            if stat.st_size > MAX_JWKS_BYTES:
                raise TokenError("JWKS file too large")
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            keys = {}
            for jwk in raw.get("keys", []):
                kid = jwk.get("kid")
                if not kid:
                    continue
                keys[str(kid)] = _key_from_jwk(jwk, self.algorithms)
            if not keys:
                raise TokenError("JWKS file contains no usable keys")
            self._keys = keys
            self._mtime = stat.st_mtime
        return self._keys

    def key(self, kid: str | None, *, refresh: bool = False):
        keys = self._load()
        if kid is None or kid not in keys:
            raise TokenError("unknown signing key")
        return keys[kid]


class HostedJWKS:
    """Bounded HTTPS JWKS fetch with cache and one refresh for an unknown kid."""

    def __init__(self, url: str, algorithms: tuple[str, ...], timeout_seconds: float = 5.0) -> None:
        if not url.startswith("https://"):
            raise TokenError("hosted JWKS URL must be https")
        self.url = url
        self.algorithms = algorithms
        self.timeout_seconds = timeout_seconds
        self._keys: dict[str, Any] = {}
        self._fetched_at: float = 0.0

    def _fetch(self) -> None:
        with httpx.Client(
            timeout=self.timeout_seconds,
            follow_redirects=False,
            max_redirects=0,
        ) as client:
            response = client.get(self.url, headers={"Accept": "application/json"})
        if response.status_code != 200:
            raise TokenError("JWKS fetch failed")
        if len(response.content) > MAX_JWKS_BYTES:
            raise TokenError("JWKS response too large")
        raw = response.json()
        keys = {}
        for jwk in raw.get("keys", []):
            kid = jwk.get("kid")
            if not kid:
                continue
            keys[str(kid)] = _key_from_jwk(jwk, self.algorithms)
        if not keys:
            raise TokenError("JWKS contains no usable keys")
        self._keys = keys
        self._fetched_at = time.time()

    def key(self, kid: str | None, *, refresh: bool = False):
        if not self._keys or time.time() - self._fetched_at > HOSTED_CACHE_SECONDS or refresh:
            self._fetch()
        if kid is None or kid not in self._keys:
            raise TokenError("unknown signing key")
        return self._keys[kid]


class TokenVerifier:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        if settings.mode == "hosted":
            if not settings.jwks_url:
                raise TokenError("hosted mode requires W03_JWKS_URL")
            self.jwks = HostedJWKS(settings.jwks_url, settings.algorithms)
        else:
            if settings.jwks_path is None:
                raise TokenError("local mode requires W03_JWKS_PATH")
            self.jwks = LocalJWKS(settings.jwks_path, settings.algorithms)

    def verify(self, token: str) -> uuid.UUID:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise ApiError(401, "UNAUTHENTICATED", "invalid bearer token") from exc
        algorithm = header.get("alg")
        if algorithm not in self.settings.algorithms:
            raise ApiError(401, "UNAUTHENTICATED", "token algorithm is not allowed")
        kid = header.get("kid")
        try:
            key = self.jwks.key(kid)
        except TokenError:
            try:
                key = self.jwks.key(kid, refresh=True)
            except TokenError as exc:
                raise ApiError(401, "UNAUTHENTICATED", "token signing key is not trusted") from exc
        try:
            claims = jwt.decode(
                token,
                key=key,
                algorithms=list(self.settings.algorithms),
                audience=self.settings.audience,
                issuer=self.settings.issuer,
                leeway=30,
                options={
                    "require": ["exp", "sub", "aud", "iss"],
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": True,
                },
            )
        except jwt.PyJWTError as exc:
            raise ApiError(401, "UNAUTHENTICATED", "invalid bearer token") from exc
        try:
            return uuid.UUID(str(claims["sub"]))
        except (ValueError, KeyError, TypeError) as exc:
            raise ApiError(401, "UNAUTHENTICATED", "token subject must be a UUID") from exc
