import os
import json
import sqlite3
from datetime import datetime, timedelta
import pathlib
import threading

class UserProfile:
    # Class variable for the database path
    db_path = "user_profiles.db"
    # Thread-local storage for connections
    _local = threading.local()
    
    def __init__(self, user_id):
        self.user_id = user_id
        self._initialize_db()
        self.profile = self._load_profile()
    
    def _get_connection(self):
        """Get a thread-local database connection"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    def _get_cursor(self):
        """Get a cursor from the thread-local connection"""
        return self._get_connection().cursor()
        
    def _initialize_db(self):
        """Initialize the SQLite database and create tables if they don't exist"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            preferences TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        ''')
        
        # Create learning_paths table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS learning_paths (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            path_id TEXT NOT NULL,
            path_data TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            UNIQUE(user_id, path_id)
        )
        ''')
        
        # Create progress table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            path_id TEXT NOT NULL,
            current_module INTEGER NOT NULL,
            current_topic INTEGER NOT NULL,
            completed_modules TEXT NOT NULL,
            completed_topics TEXT NOT NULL,
            last_accessed TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            UNIQUE(user_id, path_id)
        )
        ''')
        
        # Create quiz_results table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS quiz_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            path_id TEXT NOT NULL,
            topic_id TEXT NOT NULL,
            score REAL NOT NULL,
            passed INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            UNIQUE(user_id, path_id, topic_id)
        )
        ''')
        
        conn.commit()
    
    def _load_profile(self):
        """Load user profile from database, create if it doesn't exist"""
        cursor = self._get_cursor()
        
        # Check if user exists
        cursor.execute("SELECT preferences FROM users WHERE user_id = ?", (self.user_id,))
        result = cursor.fetchone()
        
        if result:
            # User exists, load their data
            preferences = json.loads(result[0])
            
            # Load learning paths
            learning_paths = {}
            cursor.execute("SELECT path_id, path_data FROM learning_paths WHERE user_id = ?", (self.user_id,))
            for row in cursor.fetchall():
                path_id, path_data = row['path_id'], row['path_data']
                learning_paths[path_id] = json.loads(path_data)
            
            # Load progress
            progress = {}
            cursor.execute(
                "SELECT path_id, current_module, current_topic, completed_modules, completed_topics, last_accessed "
                "FROM progress WHERE user_id = ?", 
                (self.user_id,)
            )
            for row in cursor.fetchall():
                progress[row['path_id']] = {
                    "current_module": row['current_module'],
                    "current_topic": row['current_topic'],
                    "completed_modules": json.loads(row['completed_modules']),
                    "completed_topics": json.loads(row['completed_topics']),
                    "last_accessed": row['last_accessed']
                }
            
            # Load quiz results
            quiz_results = {}
            cursor.execute("SELECT path_id, topic_id, score, passed, timestamp FROM quiz_results WHERE user_id = ?", (self.user_id,))
            for row in cursor.fetchall():
                path_id, topic_id = row['path_id'], row['topic_id']
                if path_id not in quiz_results:
                    quiz_results[path_id] = {}
                quiz_results[path_id][topic_id] = {
                    "score": row['score'],
                    "passed": bool(row['passed']),
                    "timestamp": row['timestamp']
                }
            
            return {
                "learning_paths": learning_paths,
                "progress": progress,
                "quiz_results": quiz_results,
                "preferences": preferences
            }
        else:
            # User doesn't exist, create new profile
            now = datetime.now().isoformat()
            default_preferences = {
                "difficulty": "medium",
                "learning_style": "visual",
                "learning_level": "intermediate",
                "time_constraints": {
                    "daily_hours": 2,
                    "weekly_hours": 10,
                    "target_completion_date": None
                },
                "timeline": {
                    "start_date": None,
                    "milestones": [],
                    "completion_estimates": {}
                }
            }
            
            # Insert new user
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (user_id, preferences, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (self.user_id, json.dumps(default_preferences), now, now)
            )
            conn.commit()
            
            return {
                "learning_paths": {},
                "progress": {},
                "quiz_results": {},
                "preferences": default_preferences
            }
    
    def save_profile(self):
        """Save the profile back to the database"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Update preferences
        now = datetime.now().isoformat()
        cursor.execute(
            "UPDATE users SET preferences = ?, updated_at = ? WHERE user_id = ?",
            (json.dumps(self.profile["preferences"]), now, self.user_id)
        )
        
        # Save learning paths
        for path_id, path_data in self.profile["learning_paths"].items():
            cursor.execute(
                "INSERT OR REPLACE INTO learning_paths (user_id, path_id, path_data) VALUES (?, ?, ?)",
                (self.user_id, path_id, json.dumps(path_data))
            )
        
        # Save progress
        for path_id, progress_data in self.profile["progress"].items():
            cursor.execute(
                "INSERT OR REPLACE INTO progress (user_id, path_id, current_module, current_topic, completed_modules, completed_topics, last_accessed) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    self.user_id, 
                    path_id, 
                    progress_data["current_module"], 
                    progress_data["current_topic"],
                    json.dumps(progress_data["completed_modules"]),
                    json.dumps(progress_data["completed_topics"]),
                    progress_data.get("last_accessed", datetime.now().isoformat())
                )
            )
        
        # Save quiz results
        for path_id, topics in self.profile["quiz_results"].items():
            for topic_id, result in topics.items():
                cursor.execute(
                    "INSERT OR REPLACE INTO quiz_results (user_id, path_id, topic_id, score, passed, timestamp) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        self.user_id, 
                        path_id, 
                        topic_id, 
                        result["score"], 
                        1 if result["passed"] else 0,
                        result["timestamp"]
                    )
                )
        
        conn.commit()
    
    def close_connection(self):
        """Close the database connection for the current thread"""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
    
    def __del__(self):
        """Attempt to close the connection when the object is destroyed"""
        try:
            self.close_connection()
        except:
            pass
    
    def add_learning_path(self, path_id, path_data):
        self.profile["learning_paths"][path_id] = path_data
        self.profile["progress"][path_id] = {
            "current_module": 0,
            "current_topic": 0,
            "completed_modules": [],
            "completed_topics": [],
            "last_accessed": datetime.now().isoformat()
        }
        self.save_profile()
    
    def update_progress(self, path_id, module_index, topic_index, completed=False):
        if completed:
            topic_id = f"{module_index}_{topic_index}"
            if topic_id not in self.profile["progress"][path_id]["completed_topics"]:
                self.profile["progress"][path_id]["completed_topics"].append(topic_id)
            
            # Check if module is completed
            module = self.profile["learning_paths"][path_id]["modules"][module_index]
            all_topics_completed = True
            for i in range(len(module["topics"])):
                if f"{module_index}_{i}" not in self.profile["progress"][path_id]["completed_topics"]:
                    all_topics_completed = False
                    break
            
            if all_topics_completed and module_index not in self.profile["progress"][path_id]["completed_modules"]:
                self.profile["progress"][path_id]["completed_modules"].append(module_index)
                
                # Move to next module
                if module_index + 1 < len(self.profile["learning_paths"][path_id]["modules"]):
                    self.profile["progress"][path_id]["current_module"] = module_index + 1
                    self.profile["progress"][path_id]["current_topic"] = 0
        else:
            self.profile["progress"][path_id]["current_module"] = module_index
            self.profile["progress"][path_id]["current_topic"] = topic_index
            
        # Update last accessed timestamp
        self.profile["progress"][path_id]["last_accessed"] = datetime.now().isoformat()
        self.save_profile()
    
    def record_quiz_result(self, path_id, module_index, topic_index, score):
        topic_id = f"{module_index}_{topic_index}"
        if path_id not in self.profile["quiz_results"]:
            self.profile["quiz_results"][path_id] = {}
        
        self.profile["quiz_results"][path_id][topic_id] = {
            "score": score,
            "passed": score >= 70,  # Assuming 70% is passing
            "timestamp": datetime.now().isoformat()
        }
        
        # If passed, mark as completed
        if score >= 70:
            self.update_progress(path_id, module_index, topic_index, completed=True)
        
        self.save_profile()
    
    def get_learning_path_progress(self, path_id):
        """Get a detailed progress summary for a learning path"""
        if path_id not in self.profile["progress"]:
            return None
            
        progress = self.profile["progress"][path_id]
        path_data = self.profile["learning_paths"][path_id]
        
        total_topics = sum(len(module["topics"]) for module in path_data["modules"])
        completed_topics = len(progress["completed_topics"])
        
        return {
            "total_modules": len(path_data["modules"]),
            "completed_modules": len(progress["completed_modules"]),
            "total_topics": total_topics,
            "completed_topics": completed_topics,
            "percentage_complete": (completed_topics / total_topics * 100) if total_topics > 0 else 0,
            "current_module": progress["current_module"],
            "current_topic": progress["current_topic"],
            "last_accessed": progress.get("last_accessed", "Never")
        }

    def update_preferences(self, learning_level=None, daily_hours=None, weekly_hours=None, target_completion_date=None):
        """Update user preferences including learning level and time constraints"""
        # Ensure preferences structure exists
        if "preferences" not in self.profile:
            self.profile["preferences"] = {}
        if "time_constraints" not in self.profile["preferences"]:
            self.profile["preferences"]["time_constraints"] = {
                "daily_hours": 2,
                "weekly_hours": 10,
                "target_completion_date": None
            }

        # Update values
        if learning_level:
            self.profile["preferences"]["learning_level"] = learning_level
        if daily_hours is not None:
            self.profile["preferences"]["time_constraints"]["daily_hours"] = daily_hours
        if weekly_hours is not None:
            self.profile["preferences"]["time_constraints"]["weekly_hours"] = weekly_hours
        if target_completion_date:
            self.profile["preferences"]["time_constraints"]["target_completion_date"] = target_completion_date
        self.save_profile()

    def update_timeline(self, path_id, start_date=None, milestone=None):
        """Update the learning timeline for a specific path"""
        if path_id not in self.profile["progress"]:
            return False

        timeline = self.profile["preferences"]["timeline"]
        if start_date:
            timeline["start_date"] = start_date
            # Calculate initial completion estimates
            self._calculate_completion_estimates(path_id)

        if milestone:
            timeline["milestones"].append({
                "date": datetime.now().isoformat(),
                "description": milestone,
                "path_id": path_id
            })

        self.save_profile()
        return True

    def _calculate_completion_estimates(self, path_id):
        """Calculate completion time estimates based on time constraints"""
        if path_id not in self.profile["learning_paths"]:
            return

        path_data = self.profile["learning_paths"][path_id]
        timeline = self.profile["preferences"]["timeline"]
        time_constraints = self.profile["preferences"]["time_constraints"]

        if not timeline["start_date"]:
            return

        # Calculate total estimated hours
        total_hours = 0
        for module in path_data["modules"]:
            # Parse estimated time string (e.g., "2 hours", "30 minutes", "6-8 hours")
            time_str = module.get("estimated_time", "0 hours")
            hours = 0
            
            try:
                # Check if it's a range like "6-8 hours"
                if "-" in time_str:
                    # Extract just the numeric part
                    numeric_part = time_str.split()[0]
                    parts = numeric_part.split("-")
                    lower = float(parts[0].strip())
                    upper = float(parts[1].strip())
                    # Use the average of the range
                    hours = (lower + upper) / 2
                # Not a range, normal processing
                elif "hour" in time_str:
                    parts = time_str.split()
                    hours = float(parts[0])
                elif "minute" in time_str:
                    parts = time_str.split()
                    hours = float(parts[0]) / 60
            except (ValueError, IndexError):
                # If we can't parse it, use a default value
                hours = 1.0
                
            total_hours += hours

        # Calculate completion date based on time constraints
        daily_hours = time_constraints["daily_hours"]
        weekly_hours = time_constraints["weekly_hours"]
        
        # Use the more restrictive constraint
        effective_daily_hours = min(daily_hours, weekly_hours / 7)
        
        # Calculate days needed
        days_needed = total_hours / effective_daily_hours
        
        # Calculate estimated completion date
        start_date = datetime.fromisoformat(timeline["start_date"])
        estimated_completion = start_date + timedelta(days=days_needed)
        
        timeline["completion_estimates"][path_id] = {
            "total_hours": total_hours,
            "days_needed": days_needed,
            "estimated_completion": estimated_completion.isoformat(),
            "effective_daily_hours": effective_daily_hours
        }
        
        self.save_profile()

    def get_timeline_status(self, path_id):
        """Get the current timeline status for a path"""
        if path_id not in self.profile["progress"]:
            return None

        # Ensure preferences and timeline structure exists
        if "preferences" not in self.profile:
            self.profile["preferences"] = {}
        if "timeline" not in self.profile["preferences"]:
            self.profile["preferences"]["timeline"] = {
                "start_date": None,
                "milestones": [],
                "completion_estimates": {}
            }
            self.save_profile()

        timeline = self.profile["preferences"]["timeline"]
        progress = self.profile["progress"][path_id]
        estimates = timeline.get("completion_estimates", {}).get(path_id, {})
        
        if not estimates or not timeline.get("start_date"):
            return None

        try:
            current_date = datetime.now()
            start_date = datetime.fromisoformat(timeline["start_date"])
            estimated_completion = datetime.fromisoformat(estimates["estimated_completion"])
            
            # Calculate progress
            total_days = (estimated_completion - start_date).days
            days_elapsed = (current_date - start_date).days
            progress_percentage = min(100, (days_elapsed / total_days) * 100) if total_days > 0 else 0
            
            # Calculate actual completion percentage
            path_data = self.profile["learning_paths"][path_id]
            total_topics = sum(len(module["topics"]) for module in path_data["modules"])
            completed_topics = len(progress["completed_topics"])
            actual_progress = (completed_topics / total_topics * 100) if total_topics > 0 else 0
            
            return {
                "start_date": timeline["start_date"],
                "estimated_completion": estimates["estimated_completion"],
                "days_elapsed": days_elapsed,
                "days_remaining": max(0, (estimated_completion - current_date).days),
                "progress_percentage": progress_percentage,
                "actual_progress": actual_progress,
                "is_on_track": actual_progress >= progress_percentage
            }
        except (KeyError, ValueError):
            return None
            
    @classmethod
    def migrate_json_to_sqlite(cls):
        """Migrate existing JSON profiles to SQLite database"""
        profiles_dir = "profiles"
        if not os.path.exists(profiles_dir):
            return False
            
        # Create a temporary UserProfile instance to initialize the database
        temp_profile = cls("temp")
        
        # Get all JSON files in the profiles directory
        json_files = [f for f in os.listdir(profiles_dir) if f.endswith('.json')]
        
        for json_file in json_files:
            try:
                # Extract user_id from filename
                user_id = os.path.splitext(json_file)[0]
                
                # Read the JSON file
                with open(os.path.join(profiles_dir, json_file), 'r') as f:
                    profile_data = json.load(f)
                
                # Create a UserProfile instance for this user
                user_profile = cls(user_id)
                
                # Set the profile data
                user_profile.profile = profile_data
                
                # Save to SQLite
                user_profile.save_profile()
                
                print(f"Migrated profile for user: {user_id}")
            except Exception as e:
                print(f"Error migrating profile {json_file}: {e}")
                
        return True