from __future__ import annotations

import streamlit as st

from app.actions import confirm_apply
from app.collection_job import run_collection
from app.collectors.linkedin import EXPERIENCE_LEVELS
from app.config import RESUME_DIR, UserSettings, load_settings, save_settings
from app.db import JobPosting, get_session, init_db
from app.linkedin_session import ensure_login
from app.resume_agent.pipeline import tailor_resume

ALL_SOURCES = ["linkedin", "adzuna", "jooble", "remoteok", "weworkremotely", "workatastartup"]

SOURCE_BADGE_COLOR = {
    "linkedin": "blue",
    "adzuna": "violet",
    "jooble": "orange",
    "remoteok": "green",
    "weworkremotely": "red",
    "workatastartup": "gray",
}


def source_badge(source: str) -> None:
    st.badge(source, color=SOURCE_BADGE_COLOR.get(source, "gray"))


st.set_page_config(page_title="Resume Tracker", layout="wide")
init_db()

page = st.sidebar.radio("Navigate", ["Today's Jobs", "History", "Settings"])

LOOKBACK_OPTIONS = {"Last 24h": 24, "Last 48h": 48, "Last 72h": 72, "Last 7 days": 168}
lookback_label = st.sidebar.selectbox("Search window", list(LOOKBACK_OPTIONS.keys()), index=0)

if st.sidebar.button("Run collection now"):
    with st.spinner("Collecting..."):
        count = run_collection(lookback_hours=LOOKBACK_OPTIONS[lookback_label])
    st.sidebar.success(f"Collected {count} new job(s) from the {lookback_label.lower()}")

if page == "Today's Jobs":
    st.title("Today's Jobs")
    settings = load_settings()

    with get_session() as session:
        jobs = (
            session.query(JobPosting)
            .filter(JobPosting.status == "pending")
            .order_by(JobPosting.posted_at.desc())
            .all()
        )

        if not jobs:
            st.info("No pending jobs. Try 'Run collection now' in the sidebar.")
        else:
            present_sources = sorted({job.source for job in jobs})
            filter_col, action_col = st.columns([3, 1])
            with filter_col:
                source_filter = st.multiselect(
                    "Filter by source", present_sources, default=present_sources
                )
            jobs = [job for job in jobs if job.source in source_filter]
            with action_col:
                if st.button(f"Mark all {len(jobs)} as opened"):
                    for job in jobs:
                        confirm_apply(job.id)
                    st.rerun()

            for job in jobs:
                with st.container(border=True):
                    info_col, action_col = st.columns([4, 1])
                    with info_col:
                        source_badge(job.source)
                        st.markdown(f"**{job.title}** — {job.company}")
                        st.caption(f"{job.location} · posted {job.posted_at:%Y-%m-%d %H:%M}")
                        st.markdown(f"[Open posting to apply ↗]({job.url})")
                    with action_col:
                        if st.button("Mark as opened", key=f"apply-{job.id}"):
                            confirm_apply(job.id)
                            st.rerun()

                        tailor_key = f"tailor-result-{job.id}"
                        if st.button("Tailor resume", key=f"tailor-btn-{job.id}"):
                            try:
                                with st.spinner("Fetching job details and tailoring resume via Claude..."):
                                    st.session_state[tailor_key] = tailor_resume(job, settings.resume_path)
                            except Exception as e:
                                st.error(str(e))

                        if tailor_key in st.session_state:
                            result = st.session_state[tailor_key]
                            st.caption(result.summary)
                            st.download_button(
                                "Download DOCX",
                                data=result.docx_path.read_bytes(),
                                file_name=result.docx_path.name,
                                key=f"dl-docx-{job.id}",
                            )
                            st.download_button(
                                "Download PDF",
                                data=result.pdf_path.read_bytes(),
                                file_name=result.pdf_path.name,
                                key=f"dl-pdf-{job.id}",
                            )

elif page == "History":
    st.title("Application History")
    with get_session() as session:
        jobs = (
            session.query(JobPosting)
            .filter(JobPosting.status != "pending")
            .order_by(JobPosting.applied_at.desc())
            .all()
        )
        if not jobs:
            st.info("No applications yet.")
        else:
            for job in jobs:
                with st.container(border=True):
                    source_badge(job.source)
                    st.markdown(f"**{job.title}** — {job.company} ({job.status})")
                    applied_at = job.applied_at.strftime("%Y-%m-%d %H:%M") if job.applied_at else "-"
                    st.caption(f"applied {applied_at} · {job.status_detail}")
                    st.markdown(f"[View posting]({job.url})")

elif page == "Settings":
    st.title("Settings")
    settings = load_settings()

    st.subheader("Resume")
    uploaded_resume = st.file_uploader(
        "Browse for your resume (.docx)",
        type=["docx"],
        help="Used by the 'Tailor resume' button on each job.",
    )
    resume_path = settings.resume_path
    if uploaded_resume is not None:
        saved_path = RESUME_DIR / uploaded_resume.name
        saved_path.write_bytes(uploaded_resume.getvalue())
        resume_path = str(saved_path)
    st.caption(f"Current resume: {resume_path or '(none set -- browse above)'}")
    keywords_raw = st.text_area("Keywords (one per line)", "\n".join(settings.keywords))
    location = st.text_input("Location", settings.location)
    country_code = st.text_input("Country code (for Adzuna/Jooble)", settings.country_code)
    sources = st.multiselect(
        "Enabled sources",
        ALL_SOURCES,
        default=settings.sources_enabled,
    )

    experience_labels = st.multiselect(
        "LinkedIn experience level (leave empty for any)",
        list(EXPERIENCE_LEVELS.values()),
        default=[EXPERIENCE_LEVELS[c] for c in settings.linkedin_experience_levels],
    )
    LABEL_TO_CODE = {v: k for k, v in EXPERIENCE_LEVELS.items()}

    years_filter_on = st.checkbox(
        "Filter by years of experience (best-effort text match, not exact)",
        value=settings.min_years_experience is not None or settings.max_years_experience is not None,
    )
    min_years = max_years = None
    if years_filter_on:
        min_years, max_years = st.slider(
            "Years of experience range to show",
            min_value=0,
            max_value=30,
            value=(settings.min_years_experience or 0, settings.max_years_experience or 5),
        )
        st.caption(
            "Scans title/description for phrases like \"3 years\" and only keeps postings "
            "whose mentioned years fall in this range -- e.g. 2–3 excludes both entry-level "
            "and senior postings, not just anything above 3. Postings with no years mentioned "
            "are still shown -- and LinkedIn/WorkAtAStartup rarely have any years text to match "
            "against at all, so this filter barely affects those two sources."
        )

    if st.button("Save settings"):
        new_settings = UserSettings(
            resume_path=resume_path,
            keywords=[k.strip() for k in keywords_raw.splitlines() if k.strip()],
            location=location,
            country_code=country_code,
            sources_enabled=sources,
            linkedin_experience_levels=[LABEL_TO_CODE[label] for label in experience_labels],
            min_years_experience=min_years,
            max_years_experience=max_years,
        )
        save_settings(new_settings)
        st.success("Saved.")

    st.caption(
        "Adzuna/Jooble API keys and SMTP notification settings are set in .env, not here."
    )

    st.subheader("LinkedIn login")
    st.caption(
        "No password is stored anywhere. Click below and a browser window will open "
        "on LinkedIn's real login page for you to log in yourself; only the resulting "
        "session gets saved. Re-run this whenever the saved session expires."
    )
    if st.button("Login to LinkedIn"):
        with st.spinner("Opening browser -- log in to LinkedIn in the window that appears (up to 5 min)..."):
            try:
                ensure_login()
                st.success("LinkedIn session saved.")
            except Exception as e:
                st.error(f"Login failed or timed out: {e}")
