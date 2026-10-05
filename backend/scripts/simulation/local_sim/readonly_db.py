"""本番DBへの Read Only 接続.

`app.db` は import 時に `NEON_DATABASE_URL` からエンジンを作る。
`use_readonly_database()` は `app` を import する前に呼ぶこと。
`app.db.engine` を直接使う `app.core.gamedata` なども Read Only の接続になる。
"""

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import Engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

READONLY_URL_ENV = "NEON_READONLY_DATABASE_URL"
WRITABLE_URL_ENV = "NEON_DATABASE_URL"
READ_ONLY_OPTION = "-c default_transaction_read_only=on"

BACKEND_DIR = Path(__file__).resolve().parents[3]

# PostgreSQL の SQLSTATE。
SQLSTATE_READ_ONLY_TRANSACTION = "25006"
SQLSTATE_INSUFFICIENT_PRIVILEGE = "42501"


class ReadOnlyConfigError(RuntimeError):
    """Read Only の接続を用意できないことを表す."""


def readonly_url_with_options(raw_url: str) -> str:
    """接続文字列の `options` に `default_transaction_read_only=on` を加える.

    Neon の接続文字列は `options=endpoint%3D...` を持つことがある。
    置き換えると接続できなくなるため、既存の値の後ろに足す。
    """
    url = make_url(raw_url)
    current = url.query.get("options")
    if isinstance(current, tuple):
        current = " ".join(current)
    options = f"{current} {READ_ONLY_OPTION}" if current else READ_ONLY_OPTION
    return url.update_query_dict({"options": options}).render_as_string(
        hide_password=False
    )


def use_readonly_database() -> None:
    """`app.db` が Read Only の接続文字列でエンジンを作るように環境変数を差し替える.

    Raises:
        ReadOnlyConfigError: `NEON_READONLY_DATABASE_URL` が未設定の場合。
            `app.db` が既に import されている場合
    """
    if "app.db" in sys.modules:
        raise ReadOnlyConfigError(
            "app.db が先に import されています。書き込み可能な接続のエンジンが作られています。"
        )
    load_dotenv(BACKEND_DIR / ".env")
    raw_url = os.environ.get(READONLY_URL_ENV)
    if not raw_url:
        raise ReadOnlyConfigError(
            f"{READONLY_URL_ENV} が設定されていません。"
            f"SELECT 権限だけのロールの接続文字列を backend/.env に設定してください"
            f"（{WRITABLE_URL_ENV} は使いません）。"
        )
    # app.db の load_dotenv() は既にある環境変数を上書きしない。
    os.environ[WRITABLE_URL_ENV] = readonly_url_with_options(raw_url)


def assert_read_only_session(engine: Engine) -> None:
    """接続したトランザクションが Read Only であることを確かめる.

    Raises:
        ReadOnlyConfigError: `default_transaction_read_only` が on でない場合
    """
    with engine.connect() as conn:
        value = conn.execute(text("SHOW transaction_read_only")).scalar()
    if value != "on":
        raise ReadOnlyConfigError(
            f"接続が Read Only になっていません（transaction_read_only={value}）。"
        )


@dataclass(frozen=True)
class WriteCheck:
    """書き込みを試した結果."""

    name: str
    expected_sqlstate: str
    actual_sqlstate: str | None
    message: str

    @property
    def rejected(self) -> bool:
        """期待したエラーで書き込みが拒否されたか."""
        return self.actual_sqlstate == self.expected_sqlstate


def _try_write(
    engine: Engine, name: str, statements: list[str], expected_sqlstate: str
) -> WriteCheck:
    with engine.connect() as conn:
        try:
            for statement in statements:
                conn.execute(text(statement))
        except DBAPIError as exc:
            sqlstate = getattr(exc.orig, "pgcode", None)
            message = str(exc.orig).strip().splitlines()[0]
            return WriteCheck(name, expected_sqlstate, sqlstate, message)
        finally:
            conn.rollback()
    return WriteCheck(name, expected_sqlstate, None, "書き込みが通りました")


def check_writes_rejected(engine: Engine) -> list[WriteCheck]:
    """Read Only の2つの防御が書き込みを拒否するか試す.

    どの文も `WHERE false` で0行を対象にし、最後にロールバックする。
    防御が効いていなくても本番のデータは変わらない。
    """
    return [
        _try_write(
            engine,
            "default_transaction_read_only による UPDATE の拒否",
            ["UPDATE pilots SET name = name WHERE false"],
            SQLSTATE_READ_ONLY_TRANSACTION,
        ),
        # Read Only はセッションで解除できる。解除してもロールの権限で拒否されることを確かめる。
        _try_write(
            engine,
            "SELECT 権限だけのロールによる INSERT の拒否",
            [
                "SET TRANSACTION READ WRITE",
                "INSERT INTO pilots SELECT * FROM pilots WHERE false",
            ],
            SQLSTATE_INSUFFICIENT_PRIVILEGE,
        ),
    ]
