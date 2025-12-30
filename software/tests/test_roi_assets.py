from pathlib import Path


_SOFTWARE_DIR = Path(__file__).resolve().parents[1]


def test_templates_reference_only_range_selector():
    tpl = (_SOFTWARE_DIR / "rio-webapp" / "templates" / "index.html").read_text()
    assert "roi_selector_range.js" in tpl
    forbidden = [
        "roi_selector.js",
        "roi_selector_simple.js",
        "roi_selector_sliders.js",
        "roi_selector_improved.js",
    ]
    for name in forbidden:
        assert name not in tpl


def test_static_contains_only_expected_roi_selectors():
    static_dir = _SOFTWARE_DIR / "rio-webapp" / "static"
    existing = {p.name for p in static_dir.glob("roi_selector*.js")}
    assert existing == {"roi_selector_range.js"}
