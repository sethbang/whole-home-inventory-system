"""Startup bootstrap: reconcile Alembic state and run migrations.

The prior `cafb3d2c47a1` migration was destructive (dropped all tables on
upgrade) and was removed during the Phase 2 rebaseline. Existing databases
may still have `cafb3d2c47a1` stamped in the `alembic_version` table, which
makes `alembic upgrade head` fail with "Can't locate revision identified by
'cafb3d2c47a1'". This script clears any unknown stamp, then runs upgrades.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Keep bootstrap lightweight: the bypass flag short-circuits the settings
# fail-fast, so we can run migrations even before a real SECRET_KEY is set.
os.environ.setdefault("BYPASS_AUTH", "true")

from alembic.config import Config  # noqa: E402
from alembic.script import ScriptDirectory  # noqa: E402
from sqlalchemy import inspect, text  # noqa: E402

from alembic import command  # noqa: E402
from app.database import engine  # noqa: E402


def reconcile_alembic_state() -> None:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    script = ScriptDirectory.from_config(cfg)
    known_revisions = {rev.revision for rev in script.walk_revisions()}

    with engine.begin() as conn:
        if "alembic_version" not in inspect(conn).get_table_names():
            print("[bootstrap] no alembic_version table; migrations will create it")
            return

        stamped = [
            row[0]
            for row in conn.execute(text("SELECT version_num FROM alembic_version"))
        ]
        unknown = [rev for rev in stamped if rev not in known_revisions]
        if unknown:
            print(f"[bootstrap] clearing unknown alembic stamps: {unknown}")
            conn.execute(text("DELETE FROM alembic_version"))


def assert_certs_present() -> None:
    """Fail-fast when TLS certs aren't where uvicorn expects them.

    v2.4 stopped baking cert generation into the backend image — certs
    now come from a shared volume (frontend's mkcert/OpenSSL flow in
    dev, Caddy's ACME storage in prod). Catch the missing-volume case
    early so the error is obvious instead of cascading into a cryptic
    SSL handshake failure in uvicorn.
    """
    key = ROOT / "certs" / "key.pem"
    cert = ROOT / "certs" / "cert.pem"
    missing = [p for p in (key, cert) if not p.exists()]
    if missing:
        print(
            f"[bootstrap] ERROR: expected TLS certs at {key} and {cert}; "
            f"missing: {', '.join(str(m) for m in missing)}",
            file=sys.stderr,
        )
        print(
            "[bootstrap] Run `./bin/whis certs` on the host to produce them, "
            "or mount the shared certs volume.",
            file=sys.stderr,
        )
        sys.exit(1)


def main() -> None:
    assert_certs_present()
    reconcile_alembic_state()

    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    print("[bootstrap] running alembic upgrade head")
    command.upgrade(cfg, "head")
    print("[bootstrap] migrations complete")


if __name__ == "__main__":
    main()
