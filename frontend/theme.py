"""
Custom Gradio theme for MediVision AI — Medical blue/teal palette.
"""
from __future__ import annotations

import gradio as gr
from gradio.themes.base import Base
from gradio.themes.utils import colors, fonts, sizes


class MediVisionTheme(Base):
    """
    A premium medical-themed Gradio theme with teal/blue palette,
    clean typography, and rounded cards.
    """

    def __init__(self, **kwargs):
        super().__init__(
            primary_hue=colors.teal,
            secondary_hue=colors.blue,
            neutral_hue=colors.slate,
            font=(
                fonts.GoogleFont("Inter"),
                "ui-sans-serif",
                "system-ui",
                "sans-serif",
            ),
            font_mono=(
                fonts.GoogleFont("JetBrains Mono"),
                "ui-monospace",
                "monospace",
            ),
            **kwargs,
        )

        # Override key theme variables for a premium look
        super().set(
            # Body
            body_background_fill="linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%)",
            body_background_fill_dark="linear-gradient(135deg, #020617 0%, #0f172a 50%, #020617 100%)",
            body_text_color="#e2e8f0",
            body_text_color_dark="#e2e8f0",

            # Blocks / Panels
            block_background_fill="#1e293b",
            block_background_fill_dark="#0f172a",
            block_border_width="1px",
            block_border_color="#334155",
            block_border_color_dark="#1e293b",
            block_radius="16px",
            block_shadow="0 4px 24px rgba(0, 0, 0, 0.3)",
            block_shadow_dark="0 4px 24px rgba(0, 0, 0, 0.5)",
            block_title_text_color="#f1f5f9",
            block_title_text_color_dark="#f1f5f9",
            block_label_text_color="#94a3b8",
            block_label_text_color_dark="#94a3b8",

            # Buttons
            button_primary_background_fill="linear-gradient(135deg, #0d9488, #0891b2)",
            button_primary_background_fill_dark="linear-gradient(135deg, #0d9488, #0891b2)",
            button_primary_background_fill_hover="linear-gradient(135deg, #14b8a6, #06b6d4)",
            button_primary_text_color="#ffffff",
            button_primary_border_color="transparent",
            button_primary_shadow="0 4px 14px rgba(13, 148, 136, 0.4)",
            button_secondary_background_fill="#334155",
            button_secondary_background_fill_dark="#1e293b",
            button_secondary_text_color="#e2e8f0",
            button_secondary_border_color="#475569",
            button_large_radius="12px",
            button_small_radius="8px",

            # Inputs
            input_background_fill="#0f172a",
            input_background_fill_dark="#020617",
            input_border_color="#334155",
            input_border_color_dark="#1e293b",
            input_border_color_focus="#0d9488",
            input_radius="12px",
            input_shadow="0 2px 8px rgba(0, 0, 0, 0.2)",

            # Spacing
            layout_gap="16px",
            block_padding="20px",
        )


def get_theme() -> MediVisionTheme:
    """Return the MediVision AI Gradio theme instance."""
    return MediVisionTheme()
