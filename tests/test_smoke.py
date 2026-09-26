from pathlib import Path

from dashboard.hud import CyberneticDashboard
from vision.hand_tracker import HandTracker


def test_dashboard_has_real_modules():
    dashboard = CyberneticDashboard()
    assert len(dashboard.MODULES) == 9
    assert dashboard.next_module() == "music"


def test_hand_tracker_initializes_or_explains_unavailability():
    tracker = HandTracker()
    assert tracker.available or tracker.error
    tracker.close()


def test_3d_page_is_present():
    page = Path(__file__).parents[1] / "spatial_ui" / "three_d.html"
    assert "THREE.WebGLRenderer" in page.read_text(encoding="utf-8")
