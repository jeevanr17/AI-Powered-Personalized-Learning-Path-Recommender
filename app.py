from __future__ import annotations

import importlib
from pathlib import Path
import re

import streamlit as st

from config.settings import get_settings
from dashboard.dashboard import render_progress_chart, render_skill_radar
import database.db as database_module
from models.learner import LearnerProfile
from models.learning_path import LearningPath
from services.adaptive_engine import AdaptiveEngine
from services.assessment import AssessmentService
from services.explainer import ExplanationEngine
from services.feasibility import FeasibilityEngine
from services.llm import LLMClient
from services.mailer import send_password_reset_email
from services.path_generator import LearningPathGenerator
from services.profiler import LearnerProfiler
from services.recommender import RecommenderEngine
from services.retrieval import ResourceRetrieval
from services.skill_gap import SkillGapAnalyzer
from utils.helpers import load_json_file

# Streamlit retains imported modules between reruns. Reload local persistence code so
# schema/authentication updates are applied while developing the app.
Database = importlib.reload(database_module).Database

st.set_page_config(page_title="AI Learning Recommender", layout="wide")
settings = get_settings()

try:
    db = Database()
    database_error = None
except RuntimeError as error:
    db = None
    database_error = str(error)


def load_role_target(role_name: str) -> dict[str, int]:
    roles = load_json_file(Path("data/skills.json")).get("roles", {})
    if role_name in roles:
        return roles[role_name].get("skills", {})
    normalized = (role_name or "").lower()
    if "software engineer" in normalized or "software engineering" in normalized or "software developer" in normalized:
        return roles.get("Software Engineer", {}).get("skills", {})
    if "data scientist" in normalized:
        return roles.get("Data Scientist", {}).get("skills", {})
    return roles.get("Machine Learning Engineer", {}).get("skills", {})


def get_role_assessment_id(role_name: str) -> str:
    normalized = (role_name or "").lower()
    if "software engineer" in normalized or "software engineering" in normalized or "software developer" in normalized:
        return "software-engineering-foundations"
    return "data-science-foundations" if "data scientist" in normalized else "ml-foundations"


def load_resources() -> list[dict]:
    return load_json_file(Path("data/resources.json"))


def adaptation_for_user(user_id: str) -> dict[str, bool]:
    feedback = " ".join(item["answer"].lower() for item in db.get_feedback_for_user(user_id))
    return {
        "prefer_easier": any(term in feedback for term in ("too difficult", "easier", "beginner")),
        "prefer_practical": any(term in feedback for term in ("practical", "project", "hands-on")),
        "prefer_shorter": any(term in feedback for term in ("shorter", "less time", "faster")),
    }


def create_learning_flow(profile: LearnerProfile, adaptation: dict[str, bool] | None = None):
    target_skills = load_role_target(profile.goal)
    gap_report = SkillGapAnalyzer().analyze(profile.current_skills, target_skills)
    missing_skills = {skill: gap for skill, gap in gap_report["gaps"].items() if gap > 0}
    learner_context = profile.interests + profile.learning_history
    candidates = ResourceRetrieval(Path("data/resources.json")).query(
        profile.goal, list(missing_skills), learner_context, profile.experience_level, limit=20
    )
    resources_by_id = {item["id"]: item for item in load_resources()}
    completed_courses = {course.lower() for course in profile.completed_courses}
    normalized_goal = profile.goal.lower()
    software_engineering_goal = any(term in normalized_goal for term in ("software engineer", "software engineering", "software developer"))
    resources = [
        resources_by_id[item["resource_id"]]
        for item in candidates
        if item["resource_id"] in resources_by_id
        and resources_by_id[item["resource_id"]].get("title", "").lower() not in completed_courses
        and set(resources_by_id[item["resource_id"]].get("skills_covered", [])) & set(target_skills)
        and (
            not software_engineering_goal
            or resources_by_id[item["resource_id"]].get("domain") in {"software-engineering", "backend", "software-engineering-project"}
        )
    ]
    ranked = RecommenderEngine().rank(
        [{"resource": resource} for resource in resources],
        missing_skills,
        profile.current_skills,
        {interest: 1 for interest in learner_context},
        profile.weekly_hours,
        adaptation,
    )
    ranked.sort(
        key=lambda candidate: (
            sum(profile.current_skills.get(skill, 0) < 2 for skill in candidate["resource"].get("prerequisites", [])),
            -candidate["final_score"],
        )
    )
    feasibility = FeasibilityEngine().calculate_feasibility(
        profile.weekly_hours * 4 * profile.deadline_months,
        sum(item["resource"].get("estimated_hours", 0) for item in ranked[:8]),
    )
    for recommendation in ranked[:8]:
        resource = recommendation["resource"]
        recommendation["explanation"] = ExplanationEngine().explain(resource, profile.model_dump(), gap_report)
    path = LearningPathGenerator().generate(ranked[:8], profile.model_dump(), gap_report, feasibility)
    return gap_report, ranked, path, feasibility


def clear_active_path(regenerate: bool = False) -> None:
    st.session_state.pop("path", None)
    st.session_state.pop("active_path_id", None)
    if regenerate:
        st.session_state["regenerate_path"] = True


def save_new_path(profile: LearnerProfile) -> LearningPath:
    user_id = st.session_state["current_user"]["id"]
    gap_report, ranked, path, feasibility = create_learning_flow(profile, adaptation_for_user(user_id))
    current_path = st.session_state.get("path")
    if current_path is None:
        saved_path = db.get_latest_learning_path(user_id)
        current_path = LearningPath(**saved_path["path"]) if saved_path else None
    completed_resource_ids = {
        item.resource_id
        for phase in current_path.phases
        for item in phase.resources
        if item.completed
    } if current_path else set()
    for phase in path.phases:
        for item in phase.resources:
            item.completed = item.resource_id in completed_resource_ids
    path_id = db.save_learning_path(user_id, path.model_dump(mode="json"))
    st.session_state.update({
        "gap_report": gap_report,
        "ranked": ranked,
        "path": path,
        "feasible": feasibility,
        "active_path_id": path_id,
    })
    return path


def path_matches_goal(path: LearningPath, goal: str) -> bool:
    expected_phases = [item["name"] for item in LearningPathGenerator()._phase_plan_for_goal(goal)]
    if [phase.name for phase in path.phases] != expected_phases:
        return False
    return all(
        set(item.skills) & set(phase.skills)
        for phase in path.phases
        for item in phase.resources
    )


def get_active_path(profile: LearnerProfile) -> LearningPath | None:
    if st.session_state.pop("regenerate_path", False):
        return save_new_path(profile)
    if st.session_state.get("path") is not None:
        path = st.session_state["path"]
        return path if path_matches_goal(path, profile.goal) else save_new_path(profile)
    saved = db.get_latest_learning_path(st.session_state["current_user"]["id"])
    if saved:
        st.session_state["path"] = LearningPath(**saved["path"])
        st.session_state["active_path_id"] = saved["id"]
        return st.session_state["path"] if path_matches_goal(st.session_state["path"], profile.goal) else save_new_path(profile)
    if profile.goal:
        return save_new_path(profile)
    return None


def persist_active_path() -> None:
    db.update_learning_path(st.session_state["active_path_id"], st.session_state["path"].model_dump(mode="json"))


def parse_skills(value: str) -> dict[str, int]:
    skills: dict[str, int] = {}
    for item in value.split(","):
        if not item.strip():
            continue
        name, separator, level = item.partition(":")
        if not separator:
            continue
        try:
            skills[name.strip()] = max(0, min(5, int(level.strip())))
        except ValueError:
            continue
    return skills


if database_error:
    st.error(database_error)
    st.info("Install and start MongoDB Community Server, or set a MongoDB Atlas connection string in `.env`, then reload this page.")
    st.stop()

if "current_user" not in st.session_state:
    st.session_state["current_user"] = None

if st.session_state["current_user"] is None:
    # Do not render sidebar controls until the learner is authenticated.
    st.markdown(
        """<style>[data-testid="stSidebar"] {display: none;} [data-testid="stSidebarCollapsedControl"] {display: none;}</style>""",
        unsafe_allow_html=True,
    )
    st.title("Login / Sign up")
    st.caption("Sign in to access your personalized learning roadmap.")
    login_tab, signup_tab, reset_tab = st.tabs(["Login", "Create account", "Forgot password"])
    with login_tab:
        username = st.text_input("Username or email", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            user = db.get_user_by_login(username)
            if user and db.verify_password(user["password"], password):
                st.session_state["current_user"] = {"id": user["id"], "username": user["username"], "email": user.get("email", "")}
                saved_profile = db.get_profile_for_user(user["id"])
                st.session_state["profile"] = LearnerProfile(**saved_profile) if saved_profile else LearnerProfile()
                clear_active_path()
                st.rerun()
            else:
                st.error("Invalid username or password.")
    with signup_tab:
        username = st.text_input("Choose username", key="signup_username")
        email = st.text_input("Email address", key="signup_email")
        password = st.text_input("Create password", type="password", key="signup_password")
        if st.button("Create account"):
            if not username.strip() or not email.strip() or not password.strip():
                st.warning("Username, email, and password are required.")
            elif not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email.strip()):
                st.warning("Enter a valid email address.")
            elif len(password) < 8:
                st.warning("Use a password with at least 8 characters.")
            elif db.get_user_by_username(username):
                st.warning("That username already exists.")
            elif db.get_user_by_email(email):
                st.warning("That email address already has an account.")
            else:
                user_id = db.create_user(username, email, password)
                st.session_state["current_user"] = {"id": user_id, "username": username.strip(), "email": email.strip().lower()}
                st.session_state["profile"] = LearnerProfile()
                st.rerun()
    with reset_tab:
        st.write("Request a one-time reset code using the email address registered with your account.")
        reset_email = st.text_input("Registered email address", key="reset_email")
        if st.button("Send reset code"):
            token = db.create_password_reset_token(reset_email)
            if token:
                try:
                    email_sent = send_password_reset_email(reset_email.strip(), token)
                    if email_sent:
                        st.success("A reset code was sent to your email address. It expires in 15 minutes.")
                    elif settings.email_mode == "console":
                        st.warning("Development mode only: email is not configured. Use the reset code below, then configure SMTP before deployment.")
                        st.code(token)
                    else:
                        st.error("The reset email could not be sent. Check the SMTP settings in `.env`.")
                except Exception:
                    st.error("The reset email could not be sent. Check the SMTP settings in `.env`.")
            else:
                st.success("If that email has an account, a reset code has been sent.")
        st.divider()
        reset_code = st.text_input("Reset code", key="reset_code")
        new_password = st.text_input("New password", type="password", key="new_reset_password")
        if st.button("Reset password"):
            if len(new_password) < 8:
                st.warning("Use a password with at least 8 characters.")
            elif db.reset_password(reset_code, new_password):
                st.success("Password reset successfully. You can now sign in.")
            else:
                st.error("That reset code is invalid or has expired.")
    st.stop()

pages = ["Home", "Learner Profile", "Skill Analysis", "Learning Roadmap", "Progress", "Assessments", "AI Learning Assistant"]
st.sidebar.title("Navigation")
st.sidebar.write(f"Signed in as: {st.session_state['current_user']['username']}")
if not st.session_state["current_user"].get("email"):
    st.sidebar.warning("Add a recovery email to enable password resets.")
    recovery_email = st.sidebar.text_input("Recovery email", key="existing_user_recovery_email")
    if st.sidebar.button("Save recovery email"):
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", recovery_email.strip()):
            st.sidebar.error("Enter a valid email address.")
        elif db.get_user_by_email(recovery_email):
            st.sidebar.error("That email address already has an account.")
        else:
            db.set_user_email(st.session_state["current_user"]["id"], recovery_email)
            st.session_state["current_user"]["email"] = recovery_email.strip().lower()
            st.rerun()
if st.sidebar.button("Logout"):
    for key in ("current_user", "profile", "path", "active_path_id", "chat_loaded_for", "regenerate_path"):
        st.session_state.pop(key, None)
    st.rerun()
page = st.sidebar.radio("Go to", pages)

profile = st.session_state.setdefault("profile", LearnerProfile())

if page == "Home":
    st.title("AI-Powered Personalized Learning Path Recommender")
    st.caption("Personalized, prerequisite-aware, adaptive learning roadmaps.")
    if not profile.goal:
        st.info("Start by describing your learning goal on the Learner Profile page.")
        st.stop()
    path = get_active_path(profile)
    gap_report = st.session_state.get("gap_report") or SkillGapAnalyzer().analyze(profile.current_skills, load_role_target(profile.goal))
    st.subheader("Your next recommended action")
    first_item = next((item for phase in path.phases for item in phase.resources), None)
    st.write(first_item.title if first_item else "No matching resource is available yet.")
    st.write(f"Goal: {profile.goal} · Study time: {profile.weekly_hours} hours/week · Deadline: {profile.deadline_months} months")
    st.subheader("Major skill gaps")
    st.write(", ".join(gap_report.get("critical_gaps", [])[:5]) or "No critical gaps detected.")
    completed = sum(item.completed for phase in path.phases for item in phase.resources)
    total = sum(len(phase.resources) for phase in path.phases)
    st.progress(completed / total if total else 0.0)
    st.write(f"{completed} of {total} recommended resources completed")
    st.divider()
    if st.button("Regenerate roadmap using my latest feedback"):
        save_new_path(profile)
        st.success("Your roadmap has been regenerated using your latest profile and feedback.")

elif page == "Learner Profile":
    st.title("Learner Profile")
    st.caption("Describe your background naturally, then refine the generated profile if needed.")
    description = st.text_area("Tell me your goal, skills, interests, time available, and deadline", placeholder="I know basic Python and statistics. I want to become a Machine Learning Engineer in 6 months and can study 10 hours per week. I enjoy NLP.")
    if st.button("Build profile from description"):
        try:
            profile = LearnerProfiler().from_natural_language(description)
            st.session_state["profile"] = profile
            db.save_user_profile(st.session_state["current_user"]["id"], profile.model_dump())
            clear_active_path(regenerate=True)
            st.success("Profile created from your description. Review it below and save any edits.")
        except ValueError as error:
            st.warning(str(error))
    with st.form("profile_form"):
        goal = st.text_input("Career goal", value=profile.goal)
        experience = st.selectbox("Experience level", ["beginner", "beginner_intermediate", "intermediate", "advanced"], index=["beginner", "beginner_intermediate", "intermediate", "advanced"].index(profile.experience_level) if profile.experience_level in ["beginner", "beginner_intermediate", "intermediate", "advanced"] else 0)
        skills = st.text_input("Current skills (Skill: level, 0–5)", value=", ".join(f"{name}: {level}" for name, level in profile.current_skills.items()))
        interests = st.text_input("Interests", value=", ".join(profile.interests))
        history = st.text_input("Previous learning history", value=", ".join(profile.learning_history))
        completed_courses = st.text_input("Completed courses", value=", ".join(profile.completed_courses))
        learning_style = st.selectbox("Preferred learning style", ["self_paced", "visual", "hands_on", "structured"], index=["self_paced", "visual", "hands_on", "structured"].index(profile.preferred_learning_style) if profile.preferred_learning_style in ["self_paced", "visual", "hands_on", "structured"] else 0)
        weekly_hours = st.number_input("Weekly hours", 1, 40, max(1, profile.weekly_hours or 10))
        deadline = st.number_input("Deadline (months)", 1, 36, max(1, profile.deadline_months or 6))
        submitted = st.form_submit_button("Save profile and update roadmap")
    if submitted:
        profile = LearnerProfile(goal=goal.strip(), experience_level=experience, current_skills=parse_skills(skills), interests=[item.strip() for item in interests.split(",") if item.strip()], weekly_hours=int(weekly_hours), deadline_months=int(deadline), learning_history=[item.strip() for item in history.split(",") if item.strip()], completed_courses=[item.strip() for item in completed_courses.split(",") if item.strip()], preferred_learning_style=learning_style)
        st.session_state["profile"] = profile
        db.save_user_profile(st.session_state["current_user"]["id"], profile.model_dump())
        clear_active_path(regenerate=True)
        st.success("Profile saved. Your next roadmap will use these details.")

elif page == "Skill Analysis":
    st.title("Skill Analysis")
    target = load_role_target(profile.goal)
    report = SkillGapAnalyzer().analyze(profile.current_skills, target)
    render_skill_radar(profile.current_skills, target)
    st.subheader("Priority gaps")
    for skill in report["critical_gaps"] + report["moderate_gaps"]:
        st.write(f"- {skill}: gap {report['gaps'][skill]}")

elif page == "Learning Roadmap":
    st.title("Learning Roadmap")
    path = get_active_path(profile)
    if path is None:
        st.info("Save a profile with a goal first.")
        st.stop()
    for phase in path.phases:
        st.subheader(phase.name)
        st.write("Objectives: " + ", ".join(phase.objectives))
        for item in phase.resources:
            key = f"completed_{st.session_state['active_path_id']}_{item.resource_id}"
            completed = st.checkbox(f"{item.title} ({item.type})", value=item.completed, key=key)
            if completed != item.completed:
                item.completed = completed
                persist_active_path()
                st.rerun()
            st.caption(f"{item.difficulty} · {item.estimated_hours} hours · {', '.join(item.skills)}")
            st.write(item.explanation)
        st.write(f"Milestone: {phase.milestone}")
        st.write(f"Assessment: {phase.assessment}")
    st.divider()
    feedback = st.selectbox("How should the next roadmap adapt?", ["No change", "Make it easier", "Include more hands-on projects", "Recommend shorter resources"], key="roadmap_feedback")
    if st.button("Save feedback and adapt roadmap") and feedback != "No change":
        db.save_feedback(st.session_state["current_user"]["id"], "Roadmap preference", feedback)
        clear_active_path()
        save_new_path(profile)
        st.success("Feedback saved. Your roadmap has been regenerated.")

elif page == "Progress":
    st.title("Progress")
    path = get_active_path(profile)
    if path:
        completed = sum(item.completed for phase in path.phases for item in phase.resources)
        total = sum(len(phase.resources) for phase in path.phases)
        percent = completed / total * 100 if total else 0.0
        st.metric("Total progress", f"{percent:.1f}%")
        st.metric("Completed resources", f"{completed}/{total}")
        st.metric("Completed hours", sum(item.estimated_hours for phase in path.phases for item in phase.resources if item.completed))
        render_progress_chart({"percent_complete": percent})

elif page == "Assessments":
    st.title("Assessments")
    st.caption("Each roadmap phase has its own topic-based assessment. Complete all phase resources to unlock its checkpoint.")
    path = get_active_path(profile)
    if path is None:
        st.info("Save a profile and generate a roadmap first.")
        st.stop()
    service = AssessmentService()
    if not hasattr(service, "get_phase_assessment"):
        st.error("The assessment engine was updated. Stop Streamlit and start it again to load the phase assessments.")
        st.stop()
    for phase_number, phase in enumerate(path.phases, start=1):
        resources_complete = bool(phase.resources) and all(item.completed for item in phase.resources)
        with st.expander(f"{phase.name} — {phase.assessment}", expanded=resources_complete):
            if not phase.resources:
                st.info("This phase has no assigned resources yet. Regenerate the roadmap after updating your profile.")
                continue
            if not resources_complete:
                done = sum(item.completed for item in phase.resources)
                st.warning(f"Locked: complete all phase resources first ({done}/{len(phase.resources)} completed).")
                continue
            assessment = service.get_phase_assessment(phase_number, phase.name, phase.skills)
            st.write(assessment.description)
            responses = {
                question.id: st.radio(
                    question.question, question.options,
                    key=f"{st.session_state['active_path_id']}_{assessment.id}_{question.id}",
                )
                for question in assessment.questions
            }
            if st.button("Submit phase assessment", key=f"submit_{assessment.id}"):
                result = service.score_assessment(assessment, responses)
                db.save_assessment_result(
                    st.session_state["current_user"]["id"], assessment.id,
                    result["overall_score"], result["skill_scores"], responses,
                )
                profile.current_skills = service.update_skills(profile.current_skills, result)
                st.session_state["profile"] = profile
                db.save_user_profile(st.session_state["current_user"]["id"], profile.model_dump())
                st.metric("Score", f"{result['overall_score']}%")
                for answer in result["question_results"]:
                    if answer["is_correct"]:
                        st.success(f"Correct: {answer['question']}")
                    else:
                        st.error(f"Incorrect: {answer['question']} — Correct answer: {answer['correct_answer']}")
                    st.caption(answer["explanation"])
    st.stop()

    assessment = AssessmentService().get_assessment(get_role_assessment_id(profile.goal))
    if not assessment:
        st.warning("No assessment is available for this goal.")
        st.stop()
    responses = {question.id: st.radio(question.question, question.options, key=f"{assessment.id}_{question.id}") for question in assessment.questions}
    if st.button("Submit assessment"):
        service = AssessmentService()
        result = service.score_assessment(assessment, responses)
        db.save_assessment_result(st.session_state["current_user"]["id"], assessment.id, result["overall_score"], result["skill_scores"], responses)
        profile.current_skills = service.update_skills(profile.current_skills, result)
        st.session_state["profile"] = profile
        db.save_user_profile(st.session_state["current_user"]["id"], profile.model_dump())
        weak_skills = [skill for skill, score in result["skill_scores"].items() if score < 60]
        remediation = AdaptiveEngine().build_remediation(profile.current_skills, weak_skills)
        clear_active_path()
        save_new_path(profile)
        st.write(f"Overall score: {result['overall_score']}%")
        st.subheader("Answer review")
        for answer in result.get("question_results", []):
            if answer["is_correct"]:
                st.success(f"Correct: {answer['question']}")
            else:
                st.error(f"Incorrect: {answer['question']} — Correct answer: {answer['correct_answer']}")
            st.caption(answer["explanation"])
        if remediation["remediation_needed"]:
            st.warning("Your roadmap was updated with remediation priority for: " + ", ".join(remediation["skills"]))
        else:
            st.success("Great result. Your updated skill levels have been used to refresh the roadmap.")

elif page == "AI Learning Assistant":
    st.title("AI Learning Assistant")
    user_id = st.session_state["current_user"]["id"]
    if st.session_state.get("chat_loaded_for") != user_id:
        st.session_state["chat_messages"] = db.get_conversation(user_id)
        st.session_state["chat_loaded_for"] = user_id
    for message in st.session_state.get("chat_messages", []):
        with st.chat_message(message["role"]):
            st.write(message["content"])
    prompt = st.chat_input("Ask about your roadmap, skills, or what to study next")
    if prompt:
        db.save_conversation_message(user_id, "user", prompt)
        with st.chat_message("user"):
            st.write(prompt)
        path = get_active_path(profile)
        answer = LLMClient().answer_question(prompt, profile.model_dump(), path.model_dump() if path else {})
        db.save_conversation_message(user_id, "assistant", answer)
        with st.chat_message("assistant"):
            st.write(answer)
        st.session_state["chat_messages"] = db.get_conversation(user_id)
    st.caption("Feedback recorded on the Roadmap page is used to adapt future recommendations.")
