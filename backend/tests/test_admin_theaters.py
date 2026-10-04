"""環境タイプ・戦域・地形適正の管理APIのテスト."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.models import (
    BattleResult,
    BattleRoom,
    MasterEnvironment,
    MasterTheater,
)
from app.services.theater_service import TheaterService

ADMIN_KEY = "test_admin_key_12345"
ADMIN_HEADERS = {"X-API-Key": ADMIN_KEY}

ENVIRONMENTS = "/api/admin/environments"
THEATERS = "/api/admin/theaters"
SOLOMON = "solomon"
JUNGLE = "southeast_asia_jungle"


@pytest.fixture(autouse=True)
def admin_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """管理者APIキーを設定する."""
    monkeypatch.setenv("ADMIN_API_KEY", ADMIN_KEY)


def _environment_payload(**overrides: object) -> dict:
    payload: dict = {
        "id": "DESERT",
        "name": "砂漠",
        "description": "砂嵐が視界を遮る。",
        "sensor_range_multiplier": 0.9,
        "ranged_accuracy_penalty": 0.1,
        "ranged_penalty_ref_distance": 500.0,
        "default_obstacle_density": "SPARSE",
        "default_terrain_grade": "B",
        "viewer_preset": "GROUND",
    }
    payload.update(overrides)
    return payload


def _theater_payload(**overrides: object) -> dict:
    payload: dict = {
        "id": "odessa",
        "name": "オデッサ",
        "environment_id": "SPACE",
        "base_minovsky": 0.5,
        "minovsky_variance": 0.1,
        "obstacle_density": None,
        "hint": "ヒント",
        "description": "説明",
        "rotation_order": 30,
        "is_active": True,
    }
    payload.update(overrides)
    return payload


# --- 環境タイプ ---


def test_list_environments(client: TestClient) -> None:
    """初期データの環境タイプを環境ID順に返す."""
    response = client.get(ENVIRONMENTS, headers=ADMIN_HEADERS)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert [e["id"] for e in body] == ["FOREST", "SPACE"]
    assert body[0]["sensor_range_multiplier"] == 0.8
    assert body[0]["default_obstacle_density"] == "DENSE"


def test_environment_endpoints_require_api_key(client: TestClient) -> None:
    """APIキーが違えば 401 にする."""
    wrong = {"X-API-Key": "wrong"}
    assert client.get(ENVIRONMENTS, headers=wrong).status_code == (
        status.HTTP_401_UNAUTHORIZED
    )
    assert client.get(THEATERS, headers=wrong).status_code == (
        status.HTTP_401_UNAUTHORIZED
    )


def test_create_environment(client: TestClient, session: Session) -> None:
    """環境タイプを追加できる."""
    response = client.post(
        ENVIRONMENTS, headers=ADMIN_HEADERS, json=_environment_payload()
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == _environment_payload()
    saved = session.get(MasterEnvironment, "DESERT")
    assert saved is not None
    assert saved.viewer_preset == "GROUND"


@pytest.mark.parametrize(
    "overrides",
    [
        {"id": "desert"},
        {"id": "DES-ERT"},
        {"name": ""},
        {"sensor_range_multiplier": 0},
        {"sensor_range_multiplier": 1.1},
        {"ranged_accuracy_penalty": -0.1},
        {"ranged_accuracy_penalty": 1.1},
        {"ranged_penalty_ref_distance": 0},
        {"default_obstacle_density": "HEAVY"},
        {"default_terrain_grade": "E"},
        {"viewer_preset": "DESERT"},
    ],
)
def test_create_environment_rejects_invalid_values(
    client: TestClient, overrides: dict
) -> None:
    """IDの形式・数値の範囲・選択肢に無い値は 422 にする."""
    response = client.post(
        ENVIRONMENTS, headers=ADMIN_HEADERS, json=_environment_payload(**overrides)
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_environment_rejects_duplicate_id(client: TestClient) -> None:
    """既存のIDは 409 にする."""
    response = client.post(
        ENVIRONMENTS, headers=ADMIN_HEADERS, json=_environment_payload(id="SPACE")
    )

    assert response.status_code == status.HTTP_409_CONFLICT


def test_update_environment_changes_only_given_fields(
    client: TestClient, session: Session
) -> None:
    """指定した項目だけを変える。IDは変えられない."""
    response = client.put(
        f"{ENVIRONMENTS}/FOREST",
        headers=ADMIN_HEADERS,
        json={"id": "JUNGLE", "sensor_range_multiplier": 0.7},
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["id"] == "FOREST"
    assert body["sensor_range_multiplier"] == 0.7
    assert body["ranged_accuracy_penalty"] == 0.2
    assert session.get(MasterEnvironment, "JUNGLE") is None


def test_update_environment_validates_and_reports_missing(client: TestClient) -> None:
    """範囲外の値は 422、無い環境タイプは 404 にする."""
    invalid = client.put(
        f"{ENVIRONMENTS}/FOREST",
        headers=ADMIN_HEADERS,
        json={"ranged_accuracy_penalty": 2},
    )
    missing = client.put(
        f"{ENVIRONMENTS}/NOWHERE", headers=ADMIN_HEADERS, json={"name": "x"}
    )

    assert invalid.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert missing.status_code == status.HTTP_404_NOT_FOUND


def test_delete_environment_used_by_theater_is_rejected(client: TestClient) -> None:
    """戦域から参照されている環境タイプは削除できない."""
    response = client.delete(f"{ENVIRONMENTS}/FOREST", headers=ADMIN_HEADERS)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert JUNGLE in response.json()["detail"]


def test_delete_environment(client: TestClient, session: Session) -> None:
    """参照されていない環境タイプは削除できる."""
    client.post(ENVIRONMENTS, headers=ADMIN_HEADERS, json=_environment_payload())

    response = client.delete(f"{ENVIRONMENTS}/DESERT", headers=ADMIN_HEADERS)
    missing = client.delete(f"{ENVIRONMENTS}/DESERT", headers=ADMIN_HEADERS)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert missing.status_code == status.HTTP_404_NOT_FOUND
    assert session.get(MasterEnvironment, "DESERT") is None


# --- 戦域 ---


def test_list_theaters_includes_inactive_in_rotation_order(
    client: TestClient, session: Session
) -> None:
    """無効な戦域も含めて巡回順に返す."""
    jungle = session.get(MasterTheater, JUNGLE)
    assert jungle is not None
    jungle.is_active = False
    jungle.rotation_order = 5
    session.add(jungle)
    session.commit()

    body = client.get(THEATERS, headers=ADMIN_HEADERS).json()

    assert [t["id"] for t in body] == [JUNGLE, SOLOMON]
    assert body[0]["is_active"] is False


def test_create_theater(client: TestClient, session: Session) -> None:
    """戦域を追加できる."""
    response = client.post(
        THEATERS,
        headers=ADMIN_HEADERS,
        json=_theater_payload(obstacle_density="DENSE"),
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == _theater_payload(obstacle_density="DENSE")
    saved = session.get(MasterTheater, "odessa")
    assert saved is not None
    assert saved.obstacle_density == "DENSE"


@pytest.mark.parametrize(
    "overrides",
    [
        {"id": "Odessa"},
        {"name": ""},
        {"environment_id": "NOWHERE"},
        {"base_minovsky": 1.1},
        {"minovsky_variance": 0.6},
        {"obstacle_density": "HEAVY"},
    ],
)
def test_create_theater_rejects_invalid_values(
    client: TestClient, overrides: dict
) -> None:
    """IDの形式・無い環境タイプ・範囲外の値は 422 にする."""
    response = client.post(
        THEATERS, headers=ADMIN_HEADERS, json=_theater_payload(**overrides)
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_theater_rejects_duplicate_id(client: TestClient) -> None:
    """既存のIDは 409 にする."""
    response = client.post(
        THEATERS, headers=ADMIN_HEADERS, json=_theater_payload(id=SOLOMON)
    )

    assert response.status_code == status.HTTP_409_CONFLICT


def test_update_theater(client: TestClient) -> None:
    """指定した項目だけを変える。障害物密度は null で環境タイプの既定値に戻す."""
    set_density = client.put(
        f"{THEATERS}/{SOLOMON}",
        headers=ADMIN_HEADERS,
        json={"obstacle_density": "DENSE", "rotation_order": 25},
    ).json()
    keep_density = client.put(
        f"{THEATERS}/{SOLOMON}", headers=ADMIN_HEADERS, json={"hint": "新しいヒント"}
    ).json()
    reset_density = client.put(
        f"{THEATERS}/{SOLOMON}", headers=ADMIN_HEADERS, json={"obstacle_density": None}
    ).json()

    assert set_density["obstacle_density"] == "DENSE"
    assert set_density["rotation_order"] == 25
    assert keep_density["obstacle_density"] == "DENSE"
    assert keep_density["hint"] == "新しいヒント"
    assert reset_density["obstacle_density"] is None
    assert reset_density["name"] == "ソロモン宙域"


def test_update_theater_validates_and_reports_missing(client: TestClient) -> None:
    """無い環境タイプは 422、無い戦域は 404 にする."""
    invalid = client.put(
        f"{THEATERS}/{SOLOMON}",
        headers=ADMIN_HEADERS,
        json={"environment_id": "NOWHERE"},
    )
    missing = client.put(
        f"{THEATERS}/nowhere", headers=ADMIN_HEADERS, json={"name": "x"}
    )

    assert invalid.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert missing.status_code == status.HTTP_404_NOT_FOUND


def test_last_active_theater_cannot_be_deactivated(client: TestClient) -> None:
    """有効な戦域が1つだけなら、その戦域は無効にできない."""
    first = client.put(
        f"{THEATERS}/{JUNGLE}", headers=ADMIN_HEADERS, json={"is_active": False}
    )
    last = client.put(
        f"{THEATERS}/{SOLOMON}", headers=ADMIN_HEADERS, json={"is_active": False}
    )
    already_inactive = client.put(
        f"{THEATERS}/{JUNGLE}", headers=ADMIN_HEADERS, json={"is_active": False}
    )

    assert first.status_code == status.HTTP_200_OK
    assert last.status_code == status.HTTP_409_CONFLICT
    assert already_inactive.status_code == status.HTTP_200_OK


def test_last_active_theater_cannot_be_deleted(client: TestClient) -> None:
    """有効な戦域が1つだけなら、その戦域は削除できない."""
    client.put(f"{THEATERS}/{JUNGLE}", headers=ADMIN_HEADERS, json={"is_active": False})

    response = client.delete(f"{THEATERS}/{SOLOMON}", headers=ADMIN_HEADERS)

    assert response.status_code == status.HTTP_409_CONFLICT


def test_theater_of_unfinished_room_cannot_be_deleted(
    client: TestClient, session: Session
) -> None:
    """終了していないルームの戦域は削除できない."""
    session.add(
        BattleRoom(
            status="OPEN",
            scheduled_at=datetime.now(UTC) + timedelta(hours=1),
            theater_id=JUNGLE,
            minovsky_density=0.5,
        )
    )
    session.commit()

    response = client.delete(f"{THEATERS}/{JUNGLE}", headers=ADMIN_HEADERS)

    assert response.status_code == status.HTTP_409_CONFLICT


def test_delete_theater_keeps_past_results(
    client: TestClient, session: Session
) -> None:
    """戦域を削除しても、終了したルームとバトル結果の戦域IDは残る."""
    room = BattleRoom(
        status="COMPLETED",
        scheduled_at=datetime.now(UTC) - timedelta(days=1),
        theater_id=JUNGLE,
        minovsky_density=0.5,
    )
    result = BattleResult(
        win_loss="WIN", environment="FOREST", theater_id=JUNGLE, minovsky_density=0.5
    )
    session.add(room)
    session.add(result)
    session.commit()

    response = client.delete(f"{THEATERS}/{JUNGLE}", headers=ADMIN_HEADERS)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert session.get(MasterTheater, JUNGLE) is None
    session.refresh(room)
    session.refresh(result)
    assert room.theater_id == JUNGLE
    assert result.theater_id == JUNGLE
    [label] = TheaterService.labels_for(session, [result])
    assert label.theater_name == JUNGLE
    assert label.environment_name == "森林"


def test_delete_missing_theater(client: TestClient) -> None:
    """無い戦域は 404 にする."""
    response = client.delete(f"{THEATERS}/nowhere", headers=ADMIN_HEADERS)

    assert response.status_code == status.HTTP_404_NOT_FOUND


# --- ローテーション ---


def test_rotation_returns_14_days_by_default(client: TestClient) -> None:
    """既定で今回を含む14回分の開催を返す."""
    response = client.get(f"{THEATERS}/rotation", headers=ADMIN_HEADERS)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert len(body) == 14
    assert body[0]["is_current"] is True
    assert all(not slot["is_current"] for slot in body[1:])
    assert {slot["theater_id"] for slot in body} == {SOLOMON, JUNGLE}


@pytest.mark.parametrize("days", [0, 29])
def test_rotation_rejects_out_of_range_days(client: TestClient, days: int) -> None:
    """範囲外の日数は 422 にする."""
    response = client.get(
        f"{THEATERS}/rotation", headers=ADMIN_HEADERS, params={"days": days}
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_rotation_reflects_changes_except_open_room(
    client: TestClient, session: Session
) -> None:
    """戦域の変更は次回以降に反映する。作成済みの OPEN ルームの戦域は変えない."""
    session.add(
        BattleRoom(
            status="OPEN",
            scheduled_at=datetime.now(UTC) + timedelta(hours=1),
            theater_id=JUNGLE,
            minovsky_density=0.5,
        )
    )
    session.commit()

    client.put(f"{THEATERS}/{JUNGLE}", headers=ADMIN_HEADERS, json={"is_active": False})
    body = client.get(
        f"{THEATERS}/rotation", headers=ADMIN_HEADERS, params={"days": 5}
    ).json()

    assert body[0]["theater_id"] == JUNGLE
    assert body[0]["minovsky_density"] == 0.5
    assert [slot["theater_id"] for slot in body[1:]] == [SOLOMON] * 4


# --- 機体の地形適正 ---


def _gundam(client: TestClient) -> dict:
    listed = client.get("/api/admin/mobile-suits", headers=ADMIN_HEADERS).json()
    return next(ms for ms in listed if ms["id"] == "gundam")


def test_update_mobile_suit_terrain_adaptability(client: TestClient) -> None:
    """地形適正を保存できる。specs に含めなければ変えない."""
    gundam = _gundam(client)
    specs = {**gundam["specs"], "terrain_adaptability": {"SPACE": "S", "FOREST": "C"}}

    saved = client.put(
        "/api/admin/mobile-suits/gundam",
        headers=ADMIN_HEADERS,
        json={"specs": specs},
    )
    unchanged = client.put(
        "/api/admin/mobile-suits/gundam",
        headers=ADMIN_HEADERS,
        json={"description": "更新"},
    )

    assert saved.status_code == status.HTTP_200_OK
    assert saved.json()["specs"]["terrain_adaptability"] == {
        "SPACE": "S",
        "FOREST": "C",
    }
    assert unchanged.json()["specs"]["terrain_adaptability"] == {
        "SPACE": "S",
        "FOREST": "C",
    }


def test_update_mobile_suit_rejects_invalid_terrain_grade(client: TestClient) -> None:
    """S〜D 以外のランクは 422 にする."""
    gundam = _gundam(client)
    specs = {**gundam["specs"], "terrain_adaptability": {"SPACE": "E"}}

    response = client.put(
        "/api/admin/mobile-suits/gundam",
        headers=ADMIN_HEADERS,
        json={"specs": specs},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
