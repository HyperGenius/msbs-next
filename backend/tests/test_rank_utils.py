"""ランク変換ユーティリティのテスト."""

from app.core.rank_utils import get_rank


class TestGetRank:
    """get_rank 関数のテスト."""

    # --- HP ランクテスト ---
    def test_hp_rank_s(self):
        """HP が 2000 以上は S ランク."""
        assert get_rank("hp", 2000) == "S"
        assert get_rank("hp", 3000) == "S"

    def test_hp_rank_a(self):
        """HP が 1500〜1999 は A ランク."""
        assert get_rank("hp", 1500) == "A"
        assert get_rank("hp", 1999) == "A"

    def test_hp_rank_b(self):
        """HP が 1000〜1499 は B ランク."""
        assert get_rank("hp", 1000) == "B"
        assert get_rank("hp", 1499) == "B"
        assert get_rank("hp", 1200) == "B"  # Gundam

    def test_hp_rank_c(self):
        """HP が 700〜999 は C ランク."""
        assert get_rank("hp", 800) == "C"  # Zaku II
        assert get_rank("hp", 750) == "C"  # GM
        assert get_rank("hp", 700) == "C"

    def test_hp_rank_d(self):
        """HP が 400〜699 は D ランク."""
        assert get_rank("hp", 400) == "D"
        assert get_rank("hp", 500) == "D"

    def test_hp_rank_e(self):
        """HP が 399 以下は E ランク."""
        assert get_rank("hp", 0) == "E"
        assert get_rank("hp", 399) == "E"

    # --- 装甲 ランクテスト ---
    def test_armor_rank_s(self):
        """装甲が 100 以上は S ランク."""
        assert get_rank("armor", 100) == "S"  # Gundam
        assert get_rank("armor", 150) == "S"

    def test_armor_rank_a(self):
        """装甲が 80〜99 は A ランク."""
        assert get_rank("armor", 80) == "A"  # Dom
        assert get_rank("armor", 85) == "A"  # Gelgoog
        assert get_rank("armor", 99) == "A"

    def test_armor_rank_b(self):
        """装甲が 60〜79 は B ランク."""
        assert get_rank("armor", 60) == "B"  # Gouf
        assert get_rank("armor", 79) == "B"

    def test_armor_rank_c(self):
        """装甲が 40〜59 は C ランク."""
        assert get_rank("armor", 50) == "C"  # Zaku II
        assert get_rank("armor", 45) == "C"  # GM

    def test_armor_rank_d(self):
        """装甲が 20〜39 は D ランク."""
        assert get_rank("armor", 20) == "D"
        assert get_rank("armor", 39) == "D"

    def test_armor_rank_e(self):
        """装甲が 19 以下は E ランク."""
        assert get_rank("armor", 0) == "E"
        assert get_rank("armor", 19) == "E"

    # --- 機動性 ランクテスト ---
    def test_mobility_rank_s(self):
        """機動性が 2.0 以上は S ランク."""
        assert get_rank("mobility", 2.0) == "S"
        assert get_rank("mobility", 3.0) == "S"

    def test_mobility_rank_a(self):
        """機動性が 1.5〜1.9 は A ランク."""
        assert get_rank("mobility", 1.5) == "A"  # Gundam
        assert get_rank("mobility", 1.9) == "A"

    def test_mobility_rank_b(self):
        """機動性が 1.2〜1.4 は B ランク."""
        assert get_rank("mobility", 1.2) == "B"
        assert get_rank("mobility", 1.3) == "B"  # Gouf
        assert get_rank("mobility", 1.4) == "B"  # Gelgoog

    def test_mobility_rank_c(self):
        """機動性が 0.9〜1.1 は C ランク."""
        assert get_rank("mobility", 1.0) == "C"  # Zaku II
        assert get_rank("mobility", 1.1) == "C"  # GM

    def test_mobility_rank_d(self):
        """機動性が 0.6〜0.8 は D ランク."""
        assert get_rank("mobility", 0.8) == "D"  # Dom
        assert get_rank("mobility", 0.6) == "D"

    def test_mobility_rank_e(self):
        """機動性が 0.5 以下は E ランク."""
        assert get_rank("mobility", 0.5) == "E"
        assert get_rank("mobility", 0.0) == "E"

    # --- 未定義パラメータのフォールバック ---
    def test_unknown_stat_returns_c(self):
        """未定義のステータス名の場合はデフォルトで C を返す."""
        assert get_rank("unknown_stat", 100) == "C"
