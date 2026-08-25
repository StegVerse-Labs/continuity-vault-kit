"""TVC-resident ephemeral root-key provider for SKAP.

Production key bytes are admitted only from the TV/TVC resident credential filesystem
under /run/stegverse/tv-tvc-credentials. The provider rejects symlinks, non-root-owned
files, group/world permissions, unexpected sizes, and any path outside that root.
Key bytes are supplied only to an in-process callback and the mutable copy is wiped
immediately afterward on a best-effort basis.

This module does not create, persist, rotate, export, log, or derive authority from a
root key. Provisioning/removal of the ephemeral file remains TV/TVC resident authority.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Callable, TypeVar

T = TypeVar("T")
TVC_EPHEMERAL_ROOT = Path("/run/stegverse/tv-tvc-credentials")


class SKAPKeyProviderError(ValueError):
    pass


def validate_tvc_ephemeral_key_path(path: str | os.PathLike[str]) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        raise SKAPKeyProviderError("TVC key path must be absolute")
    root = TVC_EPHEMERAL_ROOT
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise SKAPKeyProviderError("TVC key path must remain under /run/stegverse/tv-tvc-credentials") from exc
    if candidate.name in {"", ".", ".."}:
        raise SKAPKeyProviderError("TVC key path must name one credential object")
    return candidate


class TVCResidentFileKeyProvider:
    """Resolve one 256-bit SKAP root key from TVC's ephemeral resident boundary."""

    def __init__(self, path: str | os.PathLike[str]):
        self.path = validate_tvc_ephemeral_key_path(path)

    @property
    def authority_ref(self) -> str:
        return f"tvc-resident://{self.path.name}"

    def with_key(self, consumer: Callable[[memoryview], T]) -> T:
        flags = os.O_RDONLY
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(self.path, flags)
        except OSError as exc:
            raise SKAPKeyProviderError("TVC resident SKAP key is not available") from exc
        try:
            metadata = os.fstat(fd)
            if not stat.S_ISREG(metadata.st_mode):
                raise SKAPKeyProviderError("TVC resident SKAP key source must be a regular file")
            if metadata.st_uid != 0:
                raise SKAPKeyProviderError("TVC resident SKAP key source must be root-owned")
            if stat.S_IMODE(metadata.st_mode) & 0o077:
                raise SKAPKeyProviderError("TVC resident SKAP key source must not grant group/world permissions")
            payload = os.read(fd, 33)
            if len(payload) != 32:
                raise SKAPKeyProviderError("TVC resident SKAP root key must be exactly 256 bits")
            key = bytearray(payload)
            del payload
            try:
                return consumer(memoryview(key))
            finally:
                for index in range(len(key)):
                    key[index] = 0
        finally:
            os.close(fd)
