"""Colour palette and Mantine theme shared by the dashboard layout and charts."""


COLORS = {
    "ink": "#13251f",
    "muted": "#65756e",
    "green": "#16734b",
    "green_light": "#e9f5ee",
    "blue": "#4c7fe8",
    "blue_light": "#edf2ff",
    "gold": "#c18a32",
    "gold_light": "#fbf3e5",
    "surface": "#ffffff",
    "canvas": "#f4f7f5",
    "border": "#e5ebe7",
    "red": "#a63d40",
}

# Ten shades of the brand green (index 7 = COLORS["green"]) for Mantine's colour system.
FOREST = [
    "#e9f6ee",
    "#d2eadc",
    "#a3d3b8",
    "#71bb92",
    "#48a772",
    "#2e9a5f",
    "#1f8a55",
    "#16734b",
    "#0f5e3c",
    "#08482d",
]

FONT_FAMILY = "Inter, 'Segoe UI', system-ui, -apple-system, sans-serif"

MANTINE_THEME = {
    "primaryColor": "forest",
    "primaryShade": 7,
    "colors": {"forest": FOREST},
    "fontFamily": FONT_FAMILY,
    "headings": {"fontFamily": FONT_FAMILY, "fontWeight": "700"},
    "defaultRadius": "md",
    "black": COLORS["ink"],
    "components": {
        "Paper": {"defaultProps": {"radius": "lg"}},
        "SegmentedControl": {"defaultProps": {"radius": "md"}},
        "Tabs": {"defaultProps": {"radius": "md"}},
    },
}
