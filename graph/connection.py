"""FalkorDB connection. One graph per tenant, named faultline:{tenant_id} (CONTRACT §5)."""

from __future__ import annotations

import os
from functools import lru_cache
from urllib.parse import quote

from falkordb import FalkorDB, Graph

DEFAULT_FALKOR_URL = "redis://localhost:6379"
DEFAULT_TENANT = "northwind"


def falkor_url() -> str:
    """FALKOR_URL, with FALKOR_PASSWORD added when the URL carries no credentials of its own
    (docker-compose and Railway set the password separately from the host)."""
    url = os.environ.get("FALKOR_URL", DEFAULT_FALKOR_URL)
    password = os.environ.get("FALKOR_PASSWORD")
    if password and "@" not in url.split("://", 1)[-1]:
        scheme, _, rest = url.partition("://")
        url = f"{scheme}://:{quote(password, safe='')}@{rest}"
    return url


def graph_name(tenant_id: str = DEFAULT_TENANT) -> str:
    return f"faultline:{tenant_id}"


@lru_cache(maxsize=1)
def client() -> FalkorDB:
    db = FalkorDB.from_url(falkor_url())
    # A plain Redis on the same port accepts the connection and then fails on the
    # first GRAPH.QUERY with "unknown command". Fail here instead, with the URL in the message.
    modules = db.connection.execute_command("MODULE", "LIST")
    names = {_module_name(m) for m in modules}
    if "graph" not in names:
        raise RuntimeError(
            f"{falkor_url()} is a Redis server without the FalkorDB graph module "
            f"(modules: {sorted(names) or 'none'}). Point FALKOR_URL at FalkorDB."
        )
    return db


def get_graph(tenant_id: str = DEFAULT_TENANT) -> Graph:
    return client().select_graph(graph_name(tenant_id))


def _module_name(entry) -> str:
    # MODULE LIST returns [b"name", b"graph", b"ver", 41000, ...] per module (RESP2).
    if isinstance(entry, dict):
        name = entry.get(b"name", entry.get("name", b""))
    else:
        name = entry[entry.index(b"name") + 1] if b"name" in entry else entry[1]
    return name.decode() if isinstance(name, bytes) else str(name)
