import logging
from datetime import datetime
import re
from flask import jsonify
from models import Task


def check_iq_score_condition(score):
    return score > 75  # Replace with actual IQ score condition logic


def check_interview_condition(status):
    return status == "passed_interview"  # Replace with actual interview condition logic


def validate_field(field_name, value):
    """Perform validation based on the field name and return an error message if validation fails."""
    if field_name == "email":
        pattern = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
        if not re.match(pattern, value):
            return "Invalid email format."

    elif "date" in field_name:
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return "Date must be in YYYY-MM-DD format."

    elif field_name == "timestamp":
        try:
            datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return "Timestamp must be in YYYY-MM-DD HH:MM:SS format."

    elif field_name == "passport_number":
        if not (value.isdigit() or value.isalpha()):
            return "Passport number must contain only digits."

    elif "name" in field_name:
        if not value.isalpha():
            return "Name fields must contain only alphabetic characters."

    elif field_name == "score":
        try:
            score = int(value)
            if not (0 <= score <= 100):
                return "Score must be between 0 and 100."
        except ValueError:
            return "Score must be a valid integer between 0 and 100."
    elif value == "":
        return f"Missing value for field - {field_name}"

    # Return None if validation passes
    return None

def check_duplicate_task_names(tasks):
    task_names = [task.get('task_name') for task in tasks]
    if len(task_names) != len(set(task_names)):
        return "Duplicate task names are not allowed."

def check_empty_task_names(tasks):
    for task in tasks:
        if task.get('task_name') == '':
            return "Task name cannot be empty."

def create_task_list(tasks_data):
    """Create a list of Task objects from task data dictionaries."""
    tasks = []
    for task_data in tasks_data:
        task_name = task_data.get('task_name')
        required_fields = task_data.get('required_fields', [])
        condition = task_data.get('condition')

        if not task_name:
            logging.error("Each task must have a 'task_name'")
            return None, jsonify({"error": "Each task must have a 'task_name'"}), 400

        task = Task(task_name=task_name, required_fields=required_fields, condition=condition)
        tasks.append(task)
    return tasks, None, None