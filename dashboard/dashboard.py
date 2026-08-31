from __future__ import annotations

import json
from typing import Any

import plotly.graph_objects as go
import streamlit as st


def render_skill_radar(current_skills: dict[str, int], required_skills: dict[str, int]) -> None:
    keys = sorted(set(current_skills) | set(required_skills))[:8]
    current = [current_skills.get(skill, 0) for skill in keys]
    required = [required_skills.get(skill, 0) for skill in keys]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=current, theta=keys, fill="toself", name="Current Skill Level"))
    fig.add_trace(go.Scatterpolar(r=required, theta=keys, fill="toself", name="Target Skill Level"))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=True)
    st.plotly_chart(fig, use_container_width=True)


def render_progress_chart(progress_data: dict[str, Any]) -> None:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=progress_data.get("percent_complete", 0),
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": "Roadmap completion"},
    ))
    st.plotly_chart(fig, use_container_width=True)
