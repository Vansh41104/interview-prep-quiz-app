# Interview Preparation App

A Streamlit-based web application that helps users prepare for interviews through customized quizzes on various topics.

## Overview

This Interview Preparation App allows users to generate custom interview questions based on specific topics, difficulty levels, and quantities. Users can take quizzes, receive immediate feedback, and track their progress over time.

## Features

- **User Management**: Create new learning sessions or continue with existing ones
- **Custom Quiz Generation**: Generate interview questions on any subject with adjustable difficulty levels
- **Quiz Assessment**: Take quizzes with multiple-choice questions and receive immediate scoring
- **Detailed Feedback**: Review explanations for correct and incorrect answers
- **Progress Tracking**: View your quiz history and performance metrics
- **Persistent Storage**: All quiz results are stored in a PostgreSQL database

## Requirements

- Python 3.7+
- PostgreSQL database
- Required Python packages (see Installation)

## Installation

1. Clone the repository
   ```bash
   git clone https://github.com/yourusername/interview-preparation-app.git
   cd interview-preparation-app
   ```

2. Create a virtual environment (recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install required packages
   ```bash
   pip install -r requirements.txt
   ```

4. Set up your environment variables by creating a `.env` file in the project root:
   ```
   DB_NAME=your_database_name
   DB_USER=your_database_user
   DB_PASSWORD=your_database_password
   DB_HOST=localhost
   DB_PORT=5432
   ```

5. Make sure PostgreSQL is running and the database is created

## Usage

Run the Streamlit app:
```bash
streamlit run app.py
```

The app will open in your default web browser. From there, you can:

1. Log in with an existing user ID or create a new session
2. Generate a quiz by selecting:
   - Interview subject/topic
   - Number of easy, medium, and hard questions
3. Answer the questions and submit your quiz
4. Review your results and detailed feedback
5. Check your quiz history to track your progress

## Project Structure

```
interview-preparation-app/
│
├── app.py                      # Main Streamlit application
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (create this file)
│
├── generation_agent/
│   ├── __init__.py
│   ├── quiz_generator.py       # Quiz generation logic
│   ├── user_profile.py         # User profile management
│   └── data_models.py          # Data models for quizzes and questions
│
└── README.md                   # This file
```

## Database Schema

The application uses two main tables:

1. **users** - Stores user information
   - user_id (TEXT): Primary key
   - username (TEXT): User's display name
   - email (TEXT): User's email address
   - created_at (TIMESTAMP): Account creation timestamp

2. **interview_results** - Stores quiz results
   - id (SERIAL): Primary key
   - user_id (TEXT): Foreign key to users table
   - subject (TEXT): Quiz topic
   - easy_count (INTEGER): Number of easy questions
   - medium_count (INTEGER): Number of medium questions
   - hard_count (INTEGER): Number of hard questions
   - score (REAL): Quiz score percentage
   - passed (INTEGER): Boolean (0/1) indicating pass status
   - timestamp (TIMESTAMP): Quiz completion time

## Customization

The app can be extended in several ways:

- Add more question types beyond multiple-choice
- Implement user authentication for enhanced security
- Add topic-specific question banks
- Create a more sophisticated scoring algorithm

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Contact

[Your contact information]