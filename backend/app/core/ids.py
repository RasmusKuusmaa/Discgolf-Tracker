import os
import time
import uuid


def uuid7() -> uuid.UUID:
    """Generate a UUIDv7 (RFC 9562): time-ordered, so rows sort and index by
    creation order without a separate created_at lookup."""
    unix_ms = int(time.time() * 1000)
    rand = os.urandom(10)

    time_bytes = unix_ms.to_bytes(6, byteorder="big")

    rand_a = int.from_bytes(rand[0:2], "big") & 0x0FFF
    ver_and_rand_a = (0x7 << 12) | rand_a

    rand_b = int.from_bytes(rand[2:10], "big") & 0x3FFFFFFFFFFFFFFF
    variant_and_rand_b = (0b10 << 62) | rand_b

    uuid_bytes = (
        time_bytes + ver_and_rand_a.to_bytes(2, "big") + variant_and_rand_b.to_bytes(8, "big")
    )
    return uuid.UUID(bytes=uuid_bytes)
