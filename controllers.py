from models import User, Status
from flow import (
    create_admissions_flow, get_current_step_and_task, check_user_status,
    add_step, remove_step, modify_step, progress)
from uuid import uuid4
from flask import Flask, request, jsonify
from utils import validate_field, check_duplicate_task_names, check_empty_task_names, create_task_list
import logging

# Set up logging configuration
logging.basicConfig(filename='app.log', level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s')

app = Flask(__name__)

# Store users in a dictionary
users_db = {}
users_emails = set()

def validate_task_payload(task, task_payload):
    """Validate the payload for a specific task based on required fields and types."""
    missing_fields = [field for field in task.required_fields if field not in task_payload]
    if missing_fields:
        logging.error(f"Missing required fields: {', '.join(missing_fields)}")
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

    for field in task.required_fields:
        validation_error = validate_field(field, task_payload[field])
        if validation_error:
            logging.error(f"Validation error for field '{field}': {validation_error}")
            return jsonify({"error": validation_error}), 400
    return None

def complete_task_process(user, task, task_payload):
    """Complete the task process by validating and progressing the task."""
    validation_error = validate_task_payload(task, task_payload)
    if validation_error:
        return validation_error

    condition_var = task_payload.get("condition_var")
    if task.condition and not condition_var:
        logging.error(f"Task '{task.task_name}' has condition but 'condition_var' wasn't provided")
        return jsonify({"error": f"Task '{task.task_name}' has condition but 'condition_var' wasn't provided"}), 400

    condition_value = task_payload.get(condition_var) if condition_var else None
    if not progress(user, condition_value):
        logging.error("Condition failed")
        return jsonify({"error": "Condition failed"}), 500
    logging.info(f"Task '{task.task_name}' marked as completed for user '{user.user_id}'")
    return jsonify({"status": "Task marked as completed"}), 200


@app.route('/users', methods=['POST'])
def create_user():
    """Create a new user and initialize the flow."""
    data = request.json
    email = data.get('email')
    if not email:
        logging.error("Email is required.")
        return jsonify({"error": "Email is required."}), 400
    validation_error = validate_field('email', email)
    if validation_error:
        logging.error(f"Validation error for email '{email}': {validation_error}")
        return jsonify({"error": validation_error}), 400
    if email in users_emails:
        logging.error(f"Email '{email}' already exists.")
        return jsonify({"error": "Email already exists."}), 409

    # Create a new user
    user_id = str(uuid4())
    user = User(user_id, email)

    # Add steps to user
    custom_steps_data = data.get('steps')
    steps = create_admissions_flow(custom_steps_data)
    for step in steps:
        user.add_step(step)
    users_db[user_id] = user
    users_emails.add(email)
    logging.info(f"User created with ID '{user_id}' and email '{email}'")
    return jsonify({"user_id": user_id}), 201


@app.route('/users/<user_id>/flow', methods=['GET'])
def get_flow(user_id):
    """Get the entire flow for the user with level, step name, and status."""
    user = users_db.get(user_id)
    if not user:
        logging.error(f"User '{user_id}' not found")
        return jsonify({"error": "User not found"}), 404
    flow = [{"step_name": step.step_name, "index": index, "status": step.status.value} for index, step in enumerate(user.steps)]
    logging.info(f"Flow retrieved for user '{user_id}'")
    return jsonify({"flow": flow}), 200

@app.route('/users/<user_id>/current_step', methods=['GET'])
def get_current_step_and_task_for_user(user_id):
    """Get the current step and task for the user."""
    user = users_db.get(user_id)
    if not user:
        logging.error(f"User '{user_id}' not found")
        return jsonify({"error": "User not found"}), 404

    current_step, current_task = get_current_step_and_task(user)
    logging.info(f"Current step and task retrieved for user '{user_id}'")
    return jsonify({
        "current_step": {
            "name": current_step.step_name,
            "level": user.current_step_index,
            "status": current_step.status.value
        },
        "current_task": {
            "name": current_task.task_name,
            "status": current_task.status.value
        }
    })

@app.route('/users/<user_id>/steps/<step_name>/tasks/<task_name>',
       methods=['PUT'])
def complete_task(user_id, step_name, task_name):
    """Mark a specific task as completed if it meets all validation requirements."""
    user = users_db.get(user_id)
    if not user:
        logging.error(f"User '{user_id}' not found")
        return jsonify({"error": "User not found"}), 404

    task_payload = request.json.get("task_payload")
    if not task_payload:
        logging.error("Task payload is required")
        return jsonify({"error": "Task payload is required"}), 400

    if step_name not in user.steps_names:
        logging.error(f"Step '{step_name}' does not exist for user '{user_id}'")
        return jsonify({"error": "This step do not exist"}), 404

    current_step = user.steps[user.current_step_index]
    if current_step.step_name != step_name:
        logging.error(
            f"Step '{step_name}' is not the current step for user '{user_id}'")
        return jsonify(
            {"error": f"Step '{step_name}' is not the current step"}), 400
    if task_name not in current_step.tasks_names:
        logging.error(
            f"Task '{task_name}' not found in step '{step_name}' for user '{user_id}'")
        return jsonify({"error": "Task not found."}), 404

    current_task = current_step.tasks[current_step.current_task_index]
    if current_task.task_name != task_name:
        logging.error(
            f"Task '{task_name}' is not the current task in step '{step_name}' for user '{user_id}'")
        return jsonify(
            {"error": f"Task '{task_name}' is not the current task"}), 400

    if current_task.status == Status.COMPLETED:
        logging.info(
            f"Task '{task_name}' already completed for user '{user_id}'")
        return jsonify({"status": "Task already completed"}), 400

    return complete_task_process(user, current_task, task_payload)

@app.route('/users/<user_id>/complete_step/<step_name>', methods=['PUT'])
def complete_step(user_id, step_name):
    """Mark a step as completed if all tasks meet validation requirements."""
    user = users_db.get(user_id)
    if not user:
        logging.error(f"User '{user_id}' not found")
        return jsonify({"error": "User not found"}), 404

    if step_name not in user.steps_names:
        logging.error(
            f"Step '{step_name}' does not exist for user '{user_id}'")
        return jsonify({"error": "This step do not exist"}), 404

    data = request.json
    step_payload = data.get("step_payload")
    step = user.steps[user.current_step_index]

    if step.step_name != step_name:
        logging.error(
            f"Step '{step_name}' is not the current step for user '{user_id}'")
        return jsonify(
            {"error": f"Step '{step_name}' is not the current step"}), 400

    if step.status == Status.COMPLETED:
        logging.info(
            f"Step '{step_name}' already completed for user '{user_id}'")
        return jsonify({"status": "Step already completed"}), 400

    for task in step.tasks:
        if task.status == Status.COMPLETED:
            continue

        task_payload = step_payload.get(task.task_name)
        if not task_payload:
            logging.error(
                f"Missing payload for task '{task.task_name}' in step '{step_name}' for user '{user_id}'")
            return jsonify({
                               "error": f"Missing payload for task '{task.task_name}'"}), 400

        task_response = complete_task_process(user, task, task_payload)
        if isinstance(task_response, tuple) and task_response[1] != 200:
            return task_response
    logging.info(
        f"Step '{step_name}' marked as completed for user '{user_id}'")
    return jsonify({"status": "Step marked as completed"}), 200

@app.route('/users/<user_id>/status', methods=['GET'])
def get_user_status(user_id):
    """Get the current status of the user."""
    user = users_db.get(user_id)
    if not user:
        logging.error(f"User '{user_id}' not found")
        return jsonify({"error": "User not found"}), 404

    status = check_user_status(user)
    logging.info(f"Status '{status}' retrieved for user '{user_id}'")
    return jsonify({"status": status})

@app.route('/users/<user_id>/add_step', methods=['POST'])
def add_step_to_user(user_id):
    """Add a step to the user's flow by name or index with optional tasks."""
    user = users_db.get(user_id)
    if not user:
        logging.error(f"User '{user_id}' not found")
        return jsonify({"error": "User not found"}), 404

    data = request.json
    step_name = data.get('step_name')
    if step_name == "":
        logging.error("Step name cannot be empty")
        return jsonify({"error": "Step name cannot be empty"}), 400
    if step_name in user.steps_names:
        logging.error(
            f"Step with name '{step_name}' already exists for user '{user_id}'")
        return jsonify(
            {"error": f"Step with name '{step_name}' already exists"}), 400
    index = data.get('index')
    tasks_data = data.get('tasks', [])

    empty_task_error = check_empty_task_names(tasks_data)
    if empty_task_error:
        logging.error(empty_task_error)
        return jsonify({"error": empty_task_error}), 400

    duplicate_error = check_duplicate_task_names(tasks_data)
    if duplicate_error:
        logging.error(duplicate_error)
        return jsonify({"error": duplicate_error}), 400

    tasks, error_response, status = create_task_list(tasks_data)
    if error_response:
        return error_response, status

    response, code = add_step(user, step_name, tasks=tasks,
                              index=index)
    logging.error(empty_task_error)
    return jsonify(response), code

@app.route('/users/<user_id>/remove_step', methods=['DELETE'])
def remove_step_from_user(user_id):
    """Remove a step from the user's flow by name or index."""
    user = users_db.get(user_id)
    if not user:
        logging.error(f"User '{user_id}' not found")
        return jsonify({"error": "User not found"}), 404

    data = request.json
    step_name = data.get('step_name')
    index = data.get('index')

    if step_name is not None and step_name not in user.steps_names:
        logging.error(f"Step '{step_name}' does not exist for user '{user_id}'")
        return jsonify({"error": "This step do not exist"}), 400

    if (index is not None and index == user.current_step_index) or (
            step_name is not None
            and user.steps[user.current_step_index].step_name == step_name):
        logging.error(
            f"Cannot remove an in-progress step '{step_name}' for user '{user_id}'")
        return jsonify(
            {"error": "Cannot remove an in-progress step"}), 400
    response, code = remove_step(user, step_name=step_name,
                                 index=index)
    logging.info(f"Step '{step_name}' removed for user '{user_id}'")
    return jsonify(response), code

@app.route('/users/<user_id>/modify_step', methods=['PUT'])
def modify_step_for_user(user_id):
    """Modify a step in the user's flow by name or index, with optional tasks."""
    user = users_db.get(user_id)
    if not user:
        logging.error(f"User '{user_id}' not found")
        return jsonify({"error": "User not found"}), 404

    data = request.json
    new_step_name = data.get('new_step_name')
    if new_step_name == "":
        logging.error("New step's name cannot be empty")
        return jsonify(
            {"error": "New step's name cannot be empty"}), 400
    if new_step_name in user.steps_names:
        logging.error(
            f"Step with name '{new_step_name}' already exists for user '{user_id}'")
        return jsonify({
                           "error": f"Step with name '{new_step_name}' already exists"}), 400
    step_name = data.get('step_name')
    if step_name is not None and step_name not in user.steps_names:
        logging.error(
            f"Step '{step_name}' does not exist for user '{user_id}'")
        return jsonify({"error": "This step do not exist"}), 400
    index = data.get('index')
    tasks_data = data.get('tasks', [])

    empty_task_error = check_empty_task_names(tasks_data)
    if empty_task_error:
        logging.error(empty_task_error)
        return jsonify({"error": empty_task_error}), 400

    duplicate_error = check_duplicate_task_names(tasks_data)
    if duplicate_error:
        logging.error(duplicate_error)
        return jsonify({"error": duplicate_error}), 400

    tasks, error_response, status = create_task_list(tasks_data)
    if error_response:
        return error_response, status

    response, code = modify_step(user, new_step_name,
                                 step_name=step_name, index=index,
                                 tasks=tasks)
    logging.info(
        f"Step '{step_name}' modified to '{new_step_name}' for user '{user_id}'")
    return jsonify(response), code

@app.route('/users/<user_id>/update_email', methods=['PATCH'])
def update_user_email(user_id):
    """Update a user's email."""
    user = users_db.get(user_id)
    if not user:
        logging.warning(
            f"Attempted to update email for non-existent user ID: {user_id}")
        return jsonify({"error": "User not found"}), 404

    data = request.json
    new_email = data.get('email')
    if not new_email:
        logging.error("Email is required")
        return jsonify({"error": "Email is required"}), 400

    validation_error = validate_field('email', new_email)
    if validation_error:
        logging.warning(
            f"Invalid email format for update: {new_email}")
        return jsonify({"error": validation_error}), 400
    if new_email in users_emails:
        logging.warning(
            f"Duplicate email attempted in update: {new_email}")
        return jsonify({"error": "Email already exists."}), 409

    old_email = user.email
    user.email = new_email
    users_emails.remove(old_email)
    users_emails.add(new_email)
    logging.info(
        f"User {user_id} email updated from {old_email} to {new_email}")
    return jsonify({"status": "Email updated successfully"}), 200

@app.route('/users/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Delete a user."""
    user = users_db.pop(user_id, None)
    if not user:
        logging.warning(
            f"Attempted to delete non-existent user ID: {user_id}")
        return jsonify({"error": "User not found"}), 404
    users_emails.remove(user.email)
    logging.info(f"User {user_id} deleted")
    return jsonify({"status": "User deleted"}), 200

@app.route('/users', methods=['GET'])
def get_all_users():
    """Get a list of all users."""
    users_list = [{"user_id": user_id, "email": user.email} for
                  user_id, user in users_db.items()]
    logging.info("Retrieved list of all users")
    return jsonify({"users": users_list}), 200