from urllib.parse import urlparse, parse_qs
import asyncio
import ssl
import socket

from fastapi import APIRouter

from app.core.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/diag/db-check", tags=["diagnostics"])
async def db_check():
    """Run DNS resolution and TCP/SSL connect to the configured DATABASE_URL from inside the container.

    Returns diagnostic info and logs details to the application log so you can inspect Render logs.
    """
    url = settings.DATABASE_URL
    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port or 5432
    qs = parse_qs(parsed.query)
    sslmode = qs.get("sslmode", [None])[0]
    use_ssl = False
    if sslmode is not None:
        use_ssl = sslmode != "disable"
    else:
        use_ssl = host not in {"localhost", "127.0.0.1", "::1"}

    info = {
        "database_url": (host + (":" + str(port) if port else "")),
        "sslmode": sslmode,
        "use_ssl": use_ssl,
    }

    # DNS resolution
    try:
        loop = asyncio.get_running_loop()
        addrs = await loop.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
        info["addrinfo"] = [f"{ai[4][0]}:{ai[4][1]}" for ai in addrs]
    except Exception as e:
        info["dns_error"] = str(e)

    # TCP / SSL connect
    try:
        timeout = 8
        if use_ssl:
            context = ssl.create_default_context()
            if getattr(settings, "DB_SSL_NO_VERIFY", False):
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host=host, port=port, ssl=context), timeout=timeout
            )
        else:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host=host, port=port), timeout=timeout
            )
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        info["tcp_connect"] = "ok"
    except Exception as e:
        info["tcp_error"] = str(e)

    logger.info("DB diagnostic result: %s", info)
    return info
