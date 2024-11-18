import pytest
from controllers import app, users_db, users_emails
from models import Status

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
    response = create_user(client, "invalid-email")
    assert response.status_code == 400
    assert "Invalid email format." in response.get_json()["error"]


def test_duplicate_email_registration(client):
    """Test that a user cannot register with an email that already exists."""
    create_user(client, "test@example.com")
    response = create_user(client, "test@example.com")
    assert response.status_code == 409
    assert "Email already exists." in response.get_json()["error"]


def test_get_nonexistent_user(client):
    """Test accessing a user that does not exist."""
    response = client.get('/users/nonexistent_id/flow')
    assert response.status_code == 404
    assert "User not found" in response.get_json()["error"]


def test_update_email(client):
    """Test updating a user's email to ensure validation and duplicate checks."""
    response = create_user(client, "test1@example.com")
    user_id = response.get_json()["user_id"]

    # Update to a new valid email
    response = client.patch(f'/users/{user_id}/update_email',
                          json={"email": "new_email@example.com"})
    assert response.status_code == 200

    # Try updating to an invalid email format
    response = client.patch(f'/users/{user_id}/update_email',
                          json={"email": "bademail@"})
    assert response.status_code == 400
    assert "Invalid email format." in response.get_json()["error"]

    # Try updating to an existing email
    create_user(client, "duplicate@example.com")
    response = client.patch(f'/users/{user_id}/update_email',
                          json={"email": "duplicate@example.com"})
    assert response.status_code == 409


def test_delete_user(client):
    """Test deleting a user and ensure all references are removed."""
    response = create_user(client, "test2@example.com")
    user_id = response.get_json()["user_id"]
    delete_response = client.delete(f'/users/{user_id}')
    assert delete_response.status_code == 200
    assert "User deleted" in delete_response.get_json()["status"]

    # Attempt to get the deleted user
    response = client.get(f'/users/{user_id}/flow')
    assert response.status_code == 404


def test_get_all_users(client):
    """Test retrieving a list of all users."""
    create_user(client, "user1@example.com")
    create_user(client, "user2@example.com")
    response = client.get('/users')
    assert response.status_code == 200
    assert len(response.get_json()["users"]) == 2


def test_complete_task_with_condition_failed(client):
    """Test completing a task with an invalid condition."""
    response = create_user(client, "test3@example.com")
    user_id = response.get_json()["user_id"]

    # complete the first step
    response = complete_step(client, user_id, "Personal Details Form",
                             {"Personal Details Form": {"first_name": "Bob",
                              "last_name": "Adams",
                              "email": "test3@example.com",
                              "timestamp": "2024-01-01 12:00:00"}})
    assert response.status_code == 200
    step_name = "IQ Test"
    task_name = "IQ Test"

    # Retrieve initial flow
    flow = client.get(f'/users/{user_id}/flow').get_json()

    # Attempt to complete IQ Test with a score below the threshold
    task_payload = {"test_id": "123", "score": 70,
                    "timestamp": "2024-01-01 12:00:00",
                    "condition_var": "score"}
    response = complete_task(client, user_id, step_name, task_name,
                             task_payload)
    assert response.status_code == 500
    assert "Condition failed" in response.get_json()["error"]


def test_remove_step_out_of_bounds(client):
    """Test removing a step with an invalid index or step name."""
    response = create_user(client, "test4@example.com")
    user_id = response.get_json()["user_id"]

    # Attempt to remove a non-existent step by index
    response = client.delete(f'/users/{user_id}/remove_step',
                             json={"index": 10})
    assert response.status_code == 400
    assert "Index out of range" in response.get_json()["error"]


def test_modify_nonexistent_step(client):
    """Test modifying a non-existent step by name and index."""
    response = create_user(client, "test5@example.com")
    user_id = response.get_json()["user_id"]

    # Modify step with invalid name
    response = client.put(f'/users/{user_id}/modify_step',
                          json={"step_name": "Nonexistent Step",
                                "new_step_name": "Updated Step"})
    assert response.status_code == 400
    assert "This step do not exist" in \
           response.get_json()["error"]


def test_add_step_with_existing_name(client):
    """Test adding a step with an existing step name."""
    response = create_user(client, "test6@example.com")
    user_id = response.get_json()["user_id"]

    # Add a step that already exists
    response = add_step(client, user_id, "IQ Test")
    assert response.status_code == 400
    assert "Step with name 'IQ Test' already exists" in response.get_json()[
        "error"]


def test_add_step_invalid_index(client):
    """Test adding a step with an out-of-bounds index."""
    response = create_user(client, "test7@example.com")
    user_id = response.get_json()["user_id"]

    # Add a step at an invalid index
    response = add_step(client, user_id, "New Step", index=10)
    assert response.status_code == 400
    assert "Index out of range" in response.get_json()["error"]


# Additional Good Cases

def test_complete_all_tasks_in_step_successfully(client):
    """Successfully complete all tasks in a step and verify status."""
    response = create_user(client, "complete_all_tasks@example.com")
    user_id = response.get_json()["user_id"]
    # complete first 2 steps
    response = complete_step(client, user_id, "Personal Details Form",
                             {"Personal Details Form": {"first_name": "Bob",
                                                        "last_name": "Adams",
                                                        "email": "test3@example.com",
                                                        "timestamp": "2024-01-01 12:00:00"}})
    assert response.status_code == 200
    response = complete_step(client, user_id, "IQ Test", {"IQ Test": {"test_id": "123", "score": 90,
                    "timestamp": "2024-01-01 12:00:00",
                    "condition_var": "score"}})
    assert response.status_code == 200
    # Complete Inteview step
    response = complete_step(client, user_id, "Interview",
                             {"schedule interview": {"interview_date": "2024-08-01"},
                              "perform interview": {"interview_date": "2024-08-01",
                                                    "interviewer_id": "123456789",
                                                    "decision": "passed_interview",
                                                    "condition_var": "decision"}})
    assert response.status_code == 200
    assert response.get_json()["status"] == "Step marked as completed"

    # Check if the step is marked as completed
    flow_response = client.get(f'/users/{user_id}/flow')
    flow = flow_response.get_json()["flow"]
    interview = next((step for step in flow if step["step_name"] == "Interview"), None)
    assert interview["status"] == Status.COMPLETED.value

def test_add_step_in_middle_of_flow(client):
    """Test adding a step in the middle of a flow and verify order."""
    response = create_user(client, "add_step_middle@example.com")
    user_id = response.get_json()["user_id"]

    add_step(client, user_id, "Custom Step", index=1)
    response = client.get(f'/users/{user_id}/flow')
    steps = response.get_json()["flow"]

    # Verify the order of steps
    assert steps[1]["step_name"] == "Custom Step"
    assert steps[2]["step_name"] == "IQ Test"

def test_modify_step_name_successfully(client):
    """Modify a step name and verify the change."""
    response = create_user(client, "modify_step_name@example.com")
    user_id = response.get_json()["user_id"]

    response = client.put(f'/users/{user_id}/modify_step', json={"step_name": "Payment", "new_step_name": "Security Check"})
    assert response.status_code == 200
    assert response.get_json()["status"] == f"Step modified to 'Security Check'"

    # Verify that the name change is reflected in the flow
    response = client.get(f'/users/{user_id}/flow')
    flow = response.get_json()["flow"]
    step_names = [step["step_name"] for step in flow]
    assert "Security Check" in step_names
    assert "Payment" not in step_names

# Additional Bad Cases

def test_add_duplicate_task_name_in_step(client):
    """Test attempting to add a duplicate task within the same step."""
    response = create_user(client, "duplicate_task_step@example.com")
    user_id = response.get_json()["user_id"]

    # Attempt to add a task with the same name as an existing task in Background Check
    response = add_step(client, user_id, "Background Check", [{"task_name":"first_task",
                                                               "required_fields": ["Name", "Date"]},
                                                              {"task_name":"first_task",
                                                               "required_fields": ["Name", "Date"]}])
    assert response.status_code == 400
    assert "Duplicate task names are not allowed." in response.get_json()["error"]

def test_complete_task_with_invalid_payload(client):
    """Test completing a task with an invalid payload structure."""
    response = create_user(client, "invalid_task_payload@example.com")
    user_id = response.get_json()["user_id"]

    # Attempt to complete task with a missing 'submitted' field
    response = complete_task(client, user_id, "Personal Details Form", "Personal Details Form", {"invalid_field": True})
    assert response.status_code == 400
    assert "Missing required fields" in response.get_json()["error"]

def test_add_step_with_empty_name(client):
    """Attempt to add a step with an empty name."""
    response = create_user(client, "empty_step_name@example.com")
    user_id = response.get_json()["user_id"]

    response = add_step(client, user_id, "")
    assert response.status_code == 400
    assert "Step name cannot be empty" in response.get_json()["error"]

def test_modify_step_name_to_existing_name(client):
    """Modify a step name to one that already exists in the flow."""
    response = create_user(client, "modify_to_existing_name@example.com")
    user_id = response.get_json()["user_id"]

    # Attempt to rename "IQ Test" to "Background Check"
    response = client.put(f'/users/{user_id}/modify_step', json={"step_name": "IQ Test", "new_step_name": "Interview"})
    assert response.status_code == 400
    assert "Step with name 'Interview' already exists" in response.get_json()["error"]

def test_remove_last_step(client):
    """Test removing the last step and verify the flow integrity."""
    response = create_user(client, "remove_last_step@example.com")
    user_id = response.get_json()["user_id"]

    # Remove last step, "Final Interview"
    steps = client.get(f'/users/{user_id}/flow').get_json()["flow"]
    last_index = len(steps) - 1

    response = client.delete(f'/users/{user_id}/remove_step', json={"index": last_index})
    assert response.status_code == 200
    assert "Step removed successfully" in response.get_json()["status"]

    # Verify the last step is indeed removed
    steps_after_removal = client.get(f'/users/{user_id}/flow').get_json()["flow"]
    assert len(steps_after_removal) == len(steps) - 1
    assert "Final Interview" not in [step["step_name"] for step in steps_after_removal]

def test_remove_step_in_progress(client):
    """Attempt to remove a step that is in progress."""
    response = create_user(client, "remove_in_progress@example.com")
    user_id = response.get_json()["user_id"]

    # Complete Background Form to mark step as in-progress
    complete_task(client, user_id, "Background Check", "Background Form", {"submitted": True})

    # Attempt to remove the in-progress "Background Check" step
    response = client.delete(f'/users/{user_id}/remove_step', json={"index": 0})
    assert response.status_code == 400
    assert "Cannot remove an in-progress step" in response.get_json()["error"]

def test_add_task_with_empty_name(client):
    """Attempt to add a task with an empty name."""
    response = create_user(client, "add_empty_task@example.com")
    user_id = response.get_json()["user_id"]

    # Attempt to add a step with an empty task name
    response = add_step(client, user_id, "Custom Step", tasks=[{"task_name": ""}])
    assert response.status_code == 400
    assert "Task name cannot be empty" in response.get_json()["error"]

def test_concurrent_step_modifications(client):
    """Simulate concurrent modifications to the flow to check for race conditions."""
    response = create_user(client, "concurrent_modifications@example.com")
    user_id = response.get_json()["user_id"]

    # Add steps concurrently (in test environment, simulate by rapid consecutive requests)
    add_step(client, user_id, "Step A")
    response_b = add_step(client, user_id, "Step B")
    response_c = add_step(client, user_id, "Step C", index=1)

    assert response_b.status_code == 200
    assert response_c.status_code == 200

    # Verify that steps are in expected order
    steps = client.get(f'/users/{user_id}/flow').get_json()["flow"]
    step_names = [step["step_name"] for step in steps]
    assert step_names == ['Personal Details Form', 'Step C', 'IQ Test',
                          'Interview','Sign Contract','Payment', 'Join Slack','Step A','Step B']

