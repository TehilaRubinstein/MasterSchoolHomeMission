import pytest
from controllers import app, users_db, users_emails
from models import Status
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
@pytest.fixture
def client():
    with app.test_client() as client:
        yield client
    users_db.clear()
    users_emails.clear()

# Helper functions
def create_user(client, email):
    return client.post('/users', json={"email": email})

def add_step(client, user_id, step_name, tasks=None, index=None):
    data = {"step_name": step_name, "tasks": tasks or []}
    if index is not None:
        data["index"] = index
    return client.post(f'/users/{user_id}/add_step', json=data)

def complete_task(client, user_id, step_name, task_name, task_payload):
    return client.put(f'/users/{user_id}/steps/{step_name}/tasks/{task_name}',
                      json={"task_payload": task_payload})
def complete_step(client, user_id, step_name, step_payload):
    return client.put(f'/users/{user_id}/complete_step/{step_name}',
                      json={"step_payload": step_payload})


# Test Cases

def test_create_user_with_invalid_email(client):
    """Test creating a user with invalid email format."""
    logger.info("Starting test: test_create_user_with_invalid_email")
    response = create_user(client, "invalid-email")
    logger.debug(f"Response status: {response.status_code}, Response body: {response.get_json()}")
    assert response.status_code == 400
    assert "Invalid email format." in response.get_json()["error"]
    logger.info("Test passed: test_create_user_with_invalid_email")


def test_duplicate_email_registration(client):
    """Test that a user cannot register with an email that already exists."""
    logger.info("Starting test: test_duplicate_email_registration")
    create_user(client, "test@example.com")
    response = create_user(client, "test@example.com")
    logger.debug(f"Response status: {response.status_code}, Response body: {response.get_json()}")
    assert response.status_code == 409
    assert "Email already exists." in response.get_json()["error"]
    logger.info("Test passed: test_duplicate_email_registration")


def test_get_nonexistent_user(client):
    """Test accessing a user that does not exist."""
    logger.info("Starting test: test_get_nonexistent_user")
    response = client.get('/users/nonexistent_id/flow')
    logger.debug(f"Response status: {response.status_code}, Response body: {response.get_json()}")
    assert response.status_code == 404
    assert "User not found" in response.get_json()["error"]
    logger.info("Test passed: test_get_nonexistent_user")


def test_update_email(client):
    """Test updating a user's email to ensure validation and duplicate checks."""
    logger.info("Starting test: test_update_email")
    response = create_user(client, "test1@example.com")
    user_id = response.get_json()["user_id"]

    # Update to a new valid email
    response = client.patch(f'/users/{user_id}/update_email', json={"email": "new_email@example.com"})
    logger.debug(f"Response status: {response.status_code}, Response body: {response.get_json()}")
    assert response.status_code == 200

    # Try updating to an invalid email format
    response = client.patch(f'/users/{user_id}/update_email', json={"email": "bademail@"})
    logger.debug(f"Response status: {response.status_code}, Response body: {response.get_json()}")
    assert response.status_code == 400
    assert "Invalid email format." in response.get_json()["error"]

    # Try updating to an existing email
    create_user(client, "duplicate@example.com")
    response = client.patch(f'/users/{user_id}/update_email', json={"email": "duplicate@example.com"})
    logger.debug(f"Response status: {response.status_code}, Response body: {response.get_json()}")
    assert response.status_code == 409
    logger.info("Test passed: test_update_email")


def test_delete_user(client):
    """Test deleting a user and ensure all references are removed."""
    logger.info("Starting test: test_delete_user")
    response = create_user(client, "test2@example.com")
    user_id = response.get_json()["user_id"]
    delete_response = client.delete(f'/users/{user_id}')
    logger.debug(f"Delete response status: {delete_response.status_code}, Response body: {delete_response.get_json()}")
    assert delete_response.status_code == 200
    assert "User deleted" in delete_response.get_json()["status"]

    # Attempt to get the deleted user
    response = client.get(f'/users/{user_id}/flow')
    logger.debug(f"Response status: {response.status_code}, Response body: {response.get_json()}")
    assert response.status_code == 404
    logger.info("Test passed: test_delete_user")


def test_get_all_users(client):
    """Test retrieving a list of all users."""
    logger.info("Starting test: test_get_all_users")
    create_user(client, "user1@example.com")
    create_user(client, "user2@example.com")
    response = client.get('/users')
    logger.debug(f"Response status: {response.status_code}, Response body: {response.get_json()}")
    assert response.status_code == 200
    assert len(response.get_json()["users"]) == 2
    logger.info("Test passed: test_get_all_users")


def test_complete_task_with_condition_failed(client):
    """Test completing a task with an invalid condition."""
    logger.info("Starting test: test_complete_task_with_condition_failed")
    response = create_user(client, "test3@example.com")
    user_id = response.get_json()["user_id"]

    # complete the first step
    response = complete_step(client, user_id, "Personal Details Form",
                             {"Personal Details Form": {"first_name": "Bob", "last_name": "Adams",
                              "email": "test3@example.com", "timestamp": "2024-01-01 12:00:00"}})
    logger.debug(f"Step completion response: {response.status_code}, Body: {response.get_json()}")
    assert response.status_code == 200

    # Attempt to complete IQ Test with a score below the threshold
    task_payload = {"test_id": "123", "score": 70, "timestamp": "2024-01-01 12:00:00", "condition_var": "score"}
    response = complete_task(client, user_id, "IQ Test", "IQ Test", task_payload)
    logger.debug(f"Response status: {response.status_code}, Body: {response.get_json()}")
    assert response.status_code == 500
    assert "Condition failed" in response.get_json()["error"]
    logger.info("Test passed: test_complete_task_with_condition_failed")


def test_remove_step_out_of_bounds(client):
    """Test removing a step with an invalid index or step name."""
    logger.info("Starting test: test_remove_step_out_of_bounds")
    response = create_user(client, "test4@example.com")
    user_id = response.get_json()["user_id"]

    # Attempt to remove a non-existent step by index
    response = client.delete(f'/users/{user_id}/remove_step', json={"index": 10})
    logger.debug(f"Response status: {response.status_code}, Body: {response.get_json()}")
    assert response.status_code == 400
    assert "Index out of range" in response.get_json()["error"]
    logger.info("Test passed: test_remove_step_out_of_bounds")


def test_modify_nonexistent_step(client):
    """Test modifying a non-existent step by name and index."""
    logger.info("Starting test: test_modify_nonexistent_step")
    response = create_user(client, "test5@example.com")
    user_id = response.get_json()["user_id"]

    # Modify step with invalid name
    response = client.put(f'/users/{user_id}/modify_step',
                          json={"step_name": "Nonexistent Step", "new_step_name": "Updated Step"})
    logger.debug(f"Response status: {response.status_code}, Body: {response.get_json()}")
    assert response.status_code == 400
    assert "This step do not exist" in response.get_json()["error"]
    logger.info("Test passed: test_modify_nonexistent_step")


def test_add_step_with_existing_name(client):
    """Test adding a step with an existing step name."""
    logger.info("Starting test: test_add_step_with_existing_name")
    response = create_user(client, "test6@example.com")
    user_id = response.get_json()["user_id"]

    # Add a step that already exists
    response = add_step(client, user_id, "IQ Test")
    logger.debug(f"Response status: {response.status_code}, Body: {response.get_json()}")
    assert response.status_code == 400
    assert "Step with name 'IQ Test' already exists" in response.get_json()["error"]
    logger.info("Test passed: test_add_step_with_existing_name")


def test_add_step_invalid_index(client):
    """Test adding a step with an out-of-bounds index."""
    logger.info("Starting test: test_add_step_invalid_index")
    response = create_user(client, "test7@example.com")
    user_id = response.get_json()["user_id"]

    # Add a step at an invalid index
    response = add_step(client, user_id, "New Step", index=10)
    logger.debug(f"Response status: {response.status_code}, Body: {response.get_json()}")
    assert response.status_code == 400
    assert "Index out of range" in response.get_json()["error"]
    logger.info("Test passed: test_add_step_invalid_index")


# Additional Good Cases

def test_complete_all_tasks_in_step_successfully(client):
    """Successfully complete all tasks in a step and verify status."""
    logger.info("Starting test: test_complete_all_tasks_in_step_successfully")
    response = create_user(client, "complete_all_tasks@example.com")
    user_id = response.get_json()["user_id"]
    # complete first 2 steps
    response = complete_step(client, user_id, "Personal Details Form",
                             {"Personal Details Form": {"first_name": "Bob", "last_name": "Adams",
                                                        "email": "test3@example.com", "timestamp": "2024-01-01 12:00:00"}})
    logger.debug(f"Step completion response: {response.status_code}, Body: {response.get_json()}")
    assert response.status_code == 200

    response = complete_step(client, user_id, "IQ Test", {"IQ Test": {"test_id": "123", "score": 90,
                    "timestamp": "2024-01-01 12:00:00", "condition_var": "score"}})
    logger.debug(f"Step completion response: {response.status_code}, Body: {response.get_json()}")
    assert response.status_code == 200

    # Complete Interview step
    response = complete_step(client, user_id, "Interview",
                             {"schedule interview": {"interview_date": "2024-08-01"},
                              "perform interview": {"interview_date": "2024-08-01",
                                                    "interviewer_id": "123456789",
                                                    "decision": "passed_interview",
                                                    "condition_var": "decision"}})
    logger.debug(f"Step completion response: {response.status_code}, Body: {response.get_json()}")
    assert response.status_code == 200
    assert response.get_json()["status"] == "Step marked as completed"

    # Check if the step is marked as completed
    flow_response = client.get(f'/users/{user_id}/flow')
    flow = flow_response.get_json()["flow"]
    interview = next((step for step in flow if step["step_name"] == "Interview"), None)
    assert interview["status"] == Status.COMPLETED.value
    logger.info("Test passed: test_complete_all_tasks_in_step_successfully")


def test_add_step_in_middle_of_flow(client):
    """Test adding a step in the middle of a flow and verify order."""
    logger.info("Starting test: test_add_step_in_middle_of_flow")
    response = create_user(client, "add_step_middle@example.com")
    user_id = response.get_json()["user_id"]

    logger.debug(f"Adding custom step at index 1")
    add_step(client, user_id, "Custom Step", index=1)
    response = client.get(f'/users/{user_id}/flow')
    steps = response.get_json()["flow"]

    # Verify the order of steps
    assert steps[1]["step_name"] == "Custom Step"
    assert steps[2]["step_name"] == "IQ Test"
    logger.info("Test passed: test_add_step_in_middle_of_flow")


def test_modify_step_name_successfully(client):
    """Modify a step name and verify the change."""
    logger.info("Starting test: test_modify_step_name_successfully")
    response = create_user(client, "modify_step_name@example.com")
    user_id = response.get_json()["user_id"]

    logger.debug("Renaming 'Payment' step to 'Security Check'")
    response = client.put(f'/users/{user_id}/modify_step', json={"step_name": "Payment", "new_step_name": "Security Check"})
    assert response.status_code == 200
    assert response.get_json()["status"] == f"Step modified to 'Security Check'"

    # Verify that the name change is reflected in the flow
    response = client.get(f'/users/{user_id}/flow')
    flow = response.get_json()["flow"]
    step_names = [step["step_name"] for step in flow]
    assert "Security Check" in step_names
    assert "Payment" not in step_names
    logger.info("Test passed: test_modify_step_name_successfully")


# Additional Bad Cases

def test_add_duplicate_task_name_in_step(client):
    """Test attempting to add a duplicate task within the same step."""
    logger.info("Starting test: test_add_duplicate_task_name_in_step")
    response = create_user(client, "duplicate_task_step@example.com")
    user_id = response.get_json()["user_id"]

    logger.debug("Attempting to add a duplicate task to 'Background Check'")
    response = add_step(client, user_id, "Background Check", [{"task_name": "first_task", "required_fields": ["Name", "Date"]},
                                                              {"task_name": "first_task", "required_fields": ["Name", "Date"]}])
    assert response.status_code == 400
    assert "Duplicate task names are not allowed." in response.get_json()["error"]
    logger.info("Test passed: test_add_duplicate_task_name_in_step")


def test_complete_task_with_invalid_payload(client):
    """Test completing a task with an invalid payload structure."""
    logger.info("Starting test: test_complete_task_with_invalid_payload")
    response = create_user(client, "invalid_task_payload@example.com")
    user_id = response.get_json()["user_id"]

    logger.debug("Attempting to complete task with missing 'submitted' field")
    response = complete_task(client, user_id, "Personal Details Form", "Personal Details Form", {"invalid_field": True})
    assert response.status_code == 400
    assert "Missing required fields" in response.get_json()["error"]
    logger.info("Test passed: test_complete_task_with_invalid_payload")


def test_add_step_with_empty_name(client):
    """Attempt to add a step with an empty name."""
    logger.info("Starting test: test_add_step_with_empty_name")
    response = create_user(client, "empty_step_name@example.com")
    user_id = response.get_json()["user_id"]

    logger.debug("Attempting to add a step with an empty name")
    response = add_step(client, user_id, "")
    assert response.status_code == 400
    assert "Step name cannot be empty" in response.get_json()["error"]
    logger.info("Test passed: test_add_step_with_empty_name")


def test_modify_step_name_to_existing_name(client):
    """Modify a step name to one that already exists in the flow."""
    logger.info("Starting test: test_modify_step_name_to_existing_name")
    response = create_user(client, "modify_to_existing_name@example.com")
    user_id = response.get_json()["user_id"]

    logger.debug("Attempting to rename 'IQ Test' to 'Interview'")
    response = client.put(f'/users/{user_id}/modify_step', json={"step_name": "IQ Test", "new_step_name": "Interview"})
    assert response.status_code == 400
    assert "Step with name 'Interview' already exists" in response.get_json()["error"]
    logger.info("Test passed: test_modify_step_name_to_existing_name")


def test_remove_last_step(client):
    """Test removing the last step and verify the flow integrity."""
    logger.info("Starting test: test_remove_last_step")
    response = create_user(client, "remove_last_step@example.com")
    user_id = response.get_json()["user_id"]

    logger.debug("Removing the last step: 'Final Interview'")
    steps = client.get(f'/users/{user_id}/flow').get_json()["flow"]
    last_index = len(steps) - 1

    response = client.delete(f'/users/{user_id}/remove_step', json={"index": last_index})
    assert response.status_code == 200
    assert "Step removed successfully" in response.get_json()["status"]

    # Verify the last step is indeed removed
    steps_after_removal = client.get(f'/users/{user_id}/flow').get_json()["flow"]
    assert len(steps_after_removal) == len(steps) - 1
    assert "Final Interview" not in [step["step_name"] for step in steps_after_removal]
    logger.info("Test passed: test_remove_last_step")


def test_remove_step_in_progress(client):
    """Attempt to remove a step that is in progress."""
    logger.info("Starting test: test_remove_step_in_progress")
    response = create_user(client, "remove_in_progress@example.com")
    user_id = response.get_json()["user_id"]

    # Complete Background Form to mark step as in-progress
    complete_task(client, user_id, "Background Check", "Background Form", {"submitted": True})

    logger.debug("Attempting to remove an in-progress step 'Background Check'")
    response = client.delete(f'/users/{user_id}/remove_step', json={"index": 0})
    assert response.status_code == 400
    assert "Cannot remove an in-progress step" in response.get_json()["error"]
    logger.info("Test passed: test_remove_step_in_progress")


def test_add_task_with_empty_name(client):
    """Attempt to add a task with an empty name."""
    logger.info("Starting test: test_add_task_with_empty_name")
    response = create_user(client, "add_empty_task@example.com")
    user_id = response.get_json()["user_id"]

    logger.debug("Attempting to add a task with an empty name")
    response = add_step(client, user_id, "Custom Step", tasks=[{"task_name": ""}])
    assert response.status_code == 400
    assert "Task name cannot be empty" in response.get_json()["error"]
    logger.info("Test passed: test_add_task_with_empty_name")


def test_concurrent_step_modifications(client):
    """Simulate concurrent modifications to the flow to check for race conditions."""
    logger.info("Starting test: test_concurrent_step_modifications")
    response = create_user(client, "concurrent_modifications@example.com")
    user_id = response.get_json()["user_id"]

    logger.debug("Adding steps concurrently (simulate rapid consecutive requests)")
    add_step(client, user_id, "Step A")
    response_b = add_step(client, user_id, "Step B")
    response_c = add_step(client, user_id, "Step C", index=1)

    assert response_b.status_code == 200
    assert response_c.status_code == 200

    logger.debug("Verifying that steps are in the expected order")
    steps = client.get(f'/users/{user_id}/flow').get_json()["flow"]
    step_names = [step["step_name"] for step in steps]
    assert step_names == ['Personal Details Form', 'Step C', 'IQ Test', 'Interview', 'Sign Contract', 'Payment',
                          'Join Slack', 'Step A', 'Step B']
    logger.info("Test passed: test_concurrent_step_modifications")

