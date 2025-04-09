import streamlit as st
import psycopg2
import pandas as pd
import os
from datetime import datetime
from generation_agent.user_profile import UserProfile
from generation_agent.quiz_generator import QuizGenerator, generate_dummy_assessment_quiz
from contextlib import closing
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database setup for interview results
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT')
}

def get_db_connection():
    try:
        # Full DSN approach:
        conn = psycopg2.connect(
            f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
        )
        return conn
    except Exception as e:
        st.error(f"Database connection error: {str(e)}")
        return None

def initialize_interview_db():
    """Initialize the PostgreSQL database for interview quiz results."""
    conn = get_db_connection()
    if conn:
        with closing(conn) as conn:
            cursor = conn.cursor()
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS interview_results (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                subject TEXT NOT NULL,
                easy_count INTEGER NOT NULL,
                medium_count INTEGER NOT NULL,
                hard_count INTEGER NOT NULL,
                score REAL NOT NULL,
                passed INTEGER NOT NULL,
                timestamp TIMESTAMP NOT NULL
            )
            ''')
            conn.commit()

def initialize_user_table():
    conn = get_db_connection()
    if conn:
        with closing(conn) as conn:
            cursor = conn.cursor()
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            conn.commit()

# Initialize tables when the app starts
try:
    initialize_interview_db()
    initialize_user_table()
    st.session_state.db_initialized = True
except Exception as e:
    st.error(f"Failed to initialize database: {str(e)}")
    st.session_state.db_initialized = False

# ---------------------------
# Login Functionality Section
# ---------------------------
def search_users(search_term):
    """Search for users matching the search term."""
    if not search_term:
        return []
        
    conn = get_db_connection()
    if conn:
        with closing(conn) as conn:
            cursor = conn.cursor()
            try:
                # Use LIKE query for partial matching
                cursor.execute(
                    "SELECT user_id FROM users WHERE user_id ILIKE %s ORDER BY created_at DESC LIMIT 10", 
                    (f"%{search_term}%",)
                )
                return [row[0] for row in cursor.fetchall()]
            except Exception as e:
                st.error(f"Error searching users: {str(e)}")
    return []

def create_new_user(user_id):
    """Create a new user in the database."""
    conn = get_db_connection()
    if conn:
        with closing(conn) as conn:
            cursor = conn.cursor()
            try:
                # Check if user already exists
                cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
                if cursor.fetchone():
                    return False, "User ID already exists"
                
                # Insert new user
                cursor.execute(
                    "INSERT INTO users (user_id, created_at) VALUES (%s, %s)",
                    (user_id, datetime.now())
                )
                conn.commit()
                return True, "User created successfully"
            except Exception as e:
                conn.rollback()
                return False, f"Error creating user: {str(e)}"
    return False, "Database connection failed"

def login_user(user_id):
    """Handle user login and initialize QuizGenerator."""
    try:
        conn = get_db_connection()
        if conn:
            with closing(conn) as conn:
                cursor = conn.cursor()
                # Check if user exists
                cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
                user = cursor.fetchone()
                
                if user:
                    # User exists, proceed with login
                    user_profile = UserProfile(user_id)
                    st.session_state.user_id = user_id
                    st.session_state.logged_in = True
                    st.session_state.quiz_generator = QuizGenerator()
                    return True
                else:
                    # User doesn't exist
                    st.warning(f"No user found with ID: {user_id}")
                    return False
        else:
            st.error("Database connection failed. Cannot log in.")
            return False
    except Exception as e:
        st.error(f"Error logging in: {str(e)}")
        return False

def user_login_form():
    """Display a login form that lets users either select an existing profile or create a new one."""
    st.title("Interview Preparation App - Login")
    
    # Display database status if there's an issue
    if not st.session_state.get('db_initialized', False):
        st.error("Database is not properly initialized. Please check your environment variables and connection settings.")
        if st.button("Retry Database Connection"):
            try:
                initialize_interview_db()
                initialize_user_table()
                st.session_state.db_initialized = True
                st.success("Database connection successful!")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to initialize database: {str(e)}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("👤 Find Your Learning Session")
        user_search = st.text_input("Search by user ID", placeholder="Enter your user ID...")
        
        # Only search when user has entered something
        if user_search:
            filtered_profiles = search_users(user_search)
            
            if not filtered_profiles:
                st.warning(f"No user found with ID containing '{user_search}'")
            else:
                st.success(f"Found {len(filtered_profiles)} matching user(s)")
                for profile in filtered_profiles:
                    if st.button(f"Login as {profile}", key=f"login_{profile}", use_container_width=True):
                        if login_user(profile):
                            st.success(f"Login successful! Welcome, {profile}.")
                            st.rerun()
    
    with col2:
        st.subheader("✨ Create New Session")
        new_user = st.text_input("Enter a user ID for your new session", placeholder="e.g., john_doe, student123...")
        if st.button("Create New Session", use_container_width=True):
            if not new_user:
                st.warning("Please enter a user ID")
            else:
                success, message = create_new_user(new_user)
                if success:
                    st.success(message)
                    if login_user(new_user):
                        st.success(f"Login successful! Welcome, {new_user}.")
                        st.rerun()
                else:
                    st.error(message)

# ---------------------------
# Quiz and App Functionality
# ---------------------------
# Streamlit app configuration
st.set_page_config(page_title="Interview Preparation App", layout="wide")

# Initialize session state variables
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.current_questions = []
    st.session_state.user_answers = []
    st.session_state.quiz_submitted = False
    st.session_state.quiz_results = None
    st.session_state.show_feedback = False
    st.session_state.db_initialized = False

def save_quiz_result(user_id, subject, easy_count, medium_count, hard_count, score, passed):
    """Save quiz results to the PostgreSQL database."""
    timestamp = datetime.now()
    conn = get_db_connection()
    if conn:
        with closing(conn) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO interview_results (user_id, subject, easy_count, medium_count, hard_count, score, passed, timestamp) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (user_id, subject, easy_count, medium_count, hard_count, score, 1 if passed else 0, timestamp)
            )
            conn.commit()
            return True
    return False

def get_user_quiz_history(user_id):
    """Retrieve user's quiz history from PostgreSQL."""
    conn = get_db_connection()
    if conn:
        with closing(conn) as conn:
            try:
                df = pd.read_sql_query(
                    "SELECT * FROM interview_results WHERE user_id = %s ORDER BY timestamp DESC", 
                    conn, 
                    params=(user_id,)
                )
                return df
            except Exception as e:
                st.error(f"Error fetching quiz history: {str(e)}")
    return pd.DataFrame()  # Return empty DataFrame on error

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
        
        if save_quiz_result(
            st.session_state.user_id,
            st.session_state.quiz_subject,
            easy_count,
            medium_count,
            hard_count,
            results["score"],
            results["passed"]
        ):
            st.success("Quiz submitted successfully!")
        else:
            st.error("Failed to save quiz results")
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
            try:
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
            except Exception as e:
                st.error(f"Error generating quiz: {str(e)}")

def view_history():
    """Display the user's quiz history."""
    st.subheader("Quiz History")
    history = get_user_quiz_history(st.session_state.user_id)
    if not history.empty:
        # Format the timestamp column for better readability
        if 'timestamp' in history.columns:
            history['timestamp'] = pd.to_datetime(history['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
        
        # Format other columns
        if 'score' in history.columns:
            history['score'] = history['score'].round(2)
        
        if 'passed' in history.columns:
            history['passed'] = history['passed'].map({1: 'Yes', 0: 'No'})
        
        # Display the dataframe
        st.dataframe(
            history[["subject", "score", "passed", "timestamp", "easy_count", "medium_count", "hard_count"]],
            use_container_width=True
        )
        
        # Add a download button for the history
        csv = history.to_csv(index=False)
        st.download_button(
            label="Download History as CSV",
            data=csv,
            file_name=f"{st.session_state.user_id}_quiz_history.csv",
            mime="text/csv"
        )
    else:
        st.info("No quiz history available yet.")

# ---------------------------
# Main App Logic
# ---------------------------
def main():
    if not st.session_state.logged_in:
        # Call the integrated login form
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