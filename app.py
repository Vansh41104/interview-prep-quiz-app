import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime
from generation_agent.user_profile import UserProfile
from generation_agent.quiz_generator import QuizGenerator, generate_dummy_assessment_quiz
from generation_agent.data_models import MCQQuestion, AssessmentQuiz

# Database setup for interview results
DB_PATH = "interview_quizzes.db"

def initialize_interview_db():
    """Initialize the SQLite database for interview quiz results."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS interview_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        subject TEXT NOT NULL,
        easy_count INTEGER NOT NULL,
        medium_count INTEGER NOT NULL,
        hard_count INTEGER NOT NULL,
        score REAL NOT NULL,
        passed INTEGER NOT NULL,
        timestamp TEXT NOT NULL
    )
    ''')
    conn.commit()
    conn.close()

# Initialize interview database
initialize_interview_db()

# ---------------------------
# Login Functionality Section
# ---------------------------
def login_user(user_id):
    """Handle user login and initialize QuizGenerator."""
    try:
        # Create a user profile instance (you might add more logic here)
        user_profile = UserProfile(user_id)
        st.session_state.user_id = user_id
        st.session_state.logged_in = True
        st.session_state.quiz_generator = QuizGenerator()
        st.success(f"Login successful! Welcome, {user_id}.")
        st.rerun()
    except Exception as e:
        st.error(f"Error logging in: {str(e)}")

def find_user_profiles():
    """Search for existing user profiles from the 'user_profiles.db' database."""
    profiles = []
    # Check if the database exists; if not, return empty list.
    if not os.path.exists("user_profiles.db"):
        os.makedirs("profiles", exist_ok=True)
        return profiles
    
    # Query the database for all user_ids
    conn = sqlite3.connect("user_profiles.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT user_id FROM users")
        profiles = [row['user_id'] for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        # Table might not exist yet
        profiles = []
    finally:
        conn.close()
        
    return profiles

def user_login_form():
    """Display a login form that lets users either select an existing profile or create a new one."""
    st.title("Interview Preparation App - Login")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("👤 Find Your Learning Session")
        existing_profiles = find_user_profiles()
        
        if not existing_profiles:
            st.info("No existing learning sessions found. Create a new one!")
        else:
            user_search = st.text_input("Search by user ID", placeholder="Enter your user ID...")
            filtered_profiles = []
            if user_search:
                filtered_profiles = [profile for profile in existing_profiles if user_search.lower() in profile.lower()]
                if not filtered_profiles:
                    st.warning(f"No user found with ID containing '{user_search}'")
                else:
                    st.success(f"Found {len(filtered_profiles)} matching user(s)")
            else:
                filtered_profiles = existing_profiles  # show all if no search term
            
            if filtered_profiles:
                st.subheader("Select your profile:")
                for profile in filtered_profiles:
                    if st.button(f"Login as {profile}", key=f"login_{profile}", use_container_width=True):
                        login_user(profile)
    
    with col2:
        st.subheader("✨ Create New Session")
        new_user = st.text_input("Enter a user ID for your new session", 
                                 placeholder="e.g., john_doe, student123...")
        create_button = st.button("Create New Session", use_container_width=True)
        if create_button:
            if not new_user:
                st.warning("Please enter a user ID")
            else:
                if new_user in find_user_profiles():
                    st.error("This user ID already exists. Please choose another one or select it from the existing sessions.")
                else:
                    # Here you might also want to add logic to create a new profile in the user_profiles.db database.
                    login_user(new_user)

# ---------------------------
# Quiz and App Functionality
# ---------------------------
# Streamlit app configuration
st.set_page_config(page_title="Interview Preparation App", layout="wide")
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.current_questions = []
    st.session_state.user_answers = []
    st.session_state.quiz_submitted = False
    st.session_state.quiz_results = None
    st.session_state.show_feedback = False

def save_quiz_result(user_id, subject, easy_count, medium_count, hard_count, score, passed):
    """Save quiz results to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO interview_results (user_id, subject, easy_count, medium_count, hard_count, score, passed, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, subject, easy_count, medium_count, hard_count, score, 1 if passed else 0, timestamp)
    )
    conn.commit()
    conn.close()

def get_user_quiz_history(user_id):
    """Retrieve user's quiz history."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM interview_results WHERE user_id = ?", conn, params=(user_id,))
    conn.close()
    return df

def evaluate_quiz(questions, user_answers):
    """Evaluate the quiz and return results."""
    total_questions = len(questions)
    correct = sum(1 for i, q in enumerate(questions) if user_answers[i] == q["correct_option"])
    score = (correct / total_questions) * 100
    passed = score >= 70
    feedback = []
    for i, q in enumerate(questions):
        user_answer = user_answers[i]
        feedback.append({
            "question": q["question"],
            "user_answer": q["options"][user_answer] if user_answer != -1 else "Not answered",
            "correct_answer": q["options"][q["correct_option"]],
            "is_correct": user_answer == q["correct_option"],
            "explanation": q["explanation"]
        })
    return {"score": score, "passed": passed, "feedback": feedback}

def display_quiz():
    """Display the quiz questions and collect answers."""
    if not st.session_state.current_questions:
        st.warning("No quiz generated yet. Please generate a quiz first.")
        return

    st.subheader("Your Interview Quiz")
    for i, q in enumerate(st.session_state.current_questions):
        options = q["options"]
        st.write(f"**Question {i+1} ({q['difficulty']}): {q['question']}**")
        
        if st.session_state.user_answers[i] == -1:
            answer = st.radio(f"Select your answer for Q{i+1}", options, key=f"q{i}")
        else:
            answer = st.radio(f"Select your answer for Q{i+1}", options, key=f"q{i}", index=st.session_state.user_answers[i])
        
        st.session_state.user_answers[i] = options.index(answer) if answer in options else -1

    if st.button("Submit Quiz"):
        results = evaluate_quiz(st.session_state.current_questions, st.session_state.user_answers)
        st.session_state.quiz_results = results
        st.session_state.quiz_submitted = True
        easy_count = sum(1 for q in st.session_state.current_questions if q["difficulty"] == "easy")
        medium_count = sum(1 for q in st.session_state.current_questions if q["difficulty"] == "medium")
        hard_count = sum(1 for q in st.session_state.current_questions if q["difficulty"] == "hard")
        save_quiz_result(
            st.session_state.user_id,
            st.session_state.quiz_subject,
            easy_count,
            medium_count,
            hard_count,
            results["score"],
            results["passed"]
        )
        st.success("Quiz submitted successfully!")
        st.rerun()

    if st.session_state.quiz_submitted and st.session_state.quiz_results:
        st.subheader("Quiz Results")
        st.write(f"**Score:** {st.session_state.quiz_results['score']:.2f}%")
        st.write(f"**Status:** {'Passed' if st.session_state.quiz_results['passed'] else 'Failed'}")
        if st.button("Show Detailed Feedback"):
            st.session_state.show_feedback = not st.session_state.show_feedback
        if st.session_state.show_feedback:
            for fb in st.session_state.quiz_results["feedback"]:
                st.write(f"**Question:** {fb['question']}")
                st.write(f"**Your Answer:** {fb['user_answer']}")
                st.write(f"**Correct Answer:** {fb['correct_answer']}")
                st.write(f"**Explanation:** {fb['explanation']}")
                st.write("---")

def take_quiz():
    """Generate a new quiz based on user input."""
    st.subheader("Generate New Interview Quiz")
    subject = st.text_input("Interview Subject/Topic", "Python Programming")
    col1, col2, col3 = st.columns(3)
    with col1:
        num_easy = st.slider("Easy Questions", 0, 10, 3)
    with col2:
        num_medium = st.slider("Medium Questions", 0, 10, 4)
    with col3:
        num_hard = st.slider("Hard Questions", 0, 10, 3)

    if st.button("Generate Quiz"):
        with st.spinner("Generating questions..."):
            if 'quiz_generator' in st.session_state:
                questions = st.session_state.quiz_generator.generate_assessment_quiz(subject, num_easy, num_medium, num_hard)
                if not st.session_state.quiz_generator.use_llm:
                    st.warning("Using dummy questions as AI generation is unavailable.")
            else:
                questions = generate_dummy_assessment_quiz(subject, num_easy, num_medium, num_hard)
                st.warning("Using dummy questions as AI generation is unavailable.")
            if questions:
                st.session_state.current_questions = questions
                st.session_state.user_answers = [-1] * len(questions)
                st.session_state.quiz_submitted = False
                st.session_state.quiz_results = None
                st.session_state.show_feedback = False
                st.session_state.quiz_subject = subject
                st.success(f"Generated {len(questions)} questions!")
                st.rerun()
            else:
                st.error("Failed to generate questions. Please try again.")

def view_history():
    """Display the user's quiz history."""
    st.subheader("Quiz History")
    history = get_user_quiz_history(st.session_state.user_id)
    if not history.empty:
        st.dataframe(history[["subject", "score", "passed", "timestamp", "easy_count", "medium_count", "hard_count"]])
    else:
        st.info("No quiz history available yet.")

# ---------------------------
# Main App Logic
# ---------------------------
def main():
    if not st.session_state.logged_in:
        # Instead of the original text input for user_id, call the integrated login form.
        user_login_form()
    else:
        st.title(f"Welcome, {st.session_state.user_id}!")
        menu = ["Take Quiz", "View History", "Logout"]
        choice = st.sidebar.selectbox("Menu", menu)

        if choice == "Take Quiz":
            take_quiz()
            display_quiz()
        elif choice == "View History":
            view_history()
        elif choice == "Logout":
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.quiz_generator = None
            st.session_state.current_questions = []
            st.success("Logged out successfully!")
            st.rerun()

if __name__ == "__main__":
    main()
