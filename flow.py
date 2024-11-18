from models import Step, Task, Status
from utils import check_iq_score_condition, check_interview_condition, create_task_list


def create_admissions_flow(custom_steps_data=None):
    """Create the admissions flow with default or custom steps."""
    if custom_steps_data:
        custom_steps = []
        for step_data in custom_steps_data:
            step_name = step_data.get('step_name')
            tasks_data = step_data.get('tasks', [])
            tasks, error_response, status = create_task_list(tasks_data)
            if error_response:
                raise ValueError(error_response.get_json().get('error'))
            custom_steps.append(Step(step_name, tasks))
        return custom_steps
    default_steps = [
        Step("Personal Details Form", [Task("Personal Details Form",
                                            required_fields=["first_name",
                                                             "last_name",
                                                             "email",
                                                             "timestamp"])]),
        Step("IQ Test", [Task("IQ Test", check_iq_score_condition,
                              ["test_id", "score", "timestamp",
                               "condition_var"])]),
        Step("Interview",
             [Task("schedule interview", required_fields=["interview_date"]),
              Task("perform interview", check_interview_condition,
                   ["interview_date", "interviewer_id", "decision",
                    "condition_var"])]),
        Step("Sign Contract", [Task("upload identification document",
                                    required_fields=["passport_number",
                                                     "timestamp"]),
                               Task("sign contract",
                                    required_fields=["timestamp"])]),
        Step("Payment",
             [Task("Payment", required_fields=["payment_id", "timestamp"])]),
        Step("Join Slack",
             [Task("Join Slack", required_fields=["email", "timestamp"])])
    ]
    return custom_steps_data if custom_steps_data else default_steps


def get_current_step_and_task(user):
    """Get the current step the user is on."""
    cur_step_index = user.current_step_index
    cur_task_index = user.steps[cur_step_index].current_task_index
    return user.steps[cur_step_index], user.steps[cur_step_index].tasks[
        cur_task_index]


def check_user_status(user):
    """Determine if the user is accepted, rejected, or in progress."""
    return user.status.value


def progress(user, condition_var):
    """Progress the user through the steps and tasks based on the condition."""
    cur_step, cur_task = get_current_step_and_task(user)

    if cur_task.condition is not None:
        cur_task.check_completion(condition_var)

    if cur_task.status == Status.REJECTED:
        cur_step.status = user.status = Status.REJECTED
        return False

    if cur_step.current_task_index < len(cur_step.tasks) - 1:
        cur_step.current_task_index += 1
    else:
        cur_step.status = Status.COMPLETED
        if user.current_step_index < len(user.steps) - 1:
            user.current_step_index += 1
        else:
            user.status = Status.ACCEPTED
    return True


def add_step(user, step_name, tasks, index):
    """Add a step by name or index to the user's flow."""
    step = Step(step_name, tasks)
    try:
        if index is not None:
            user.add_step(step, index)
            return {"status": f"Step '{step_name}' added at index {index}"}, 200
        else:
            user.add_step(step)
            return {"status": f"Step '{step_name}' added"}, 200
    except IndexError as e:
        return {"error": str(e)}, 400


def remove_step(user, step_name=None, index=None):
    """Remove a step by name or index from the user's flow."""
    try:
        user.remove_step(step_name=step_name, index=index)
        return {"status": "Step removed successfully"}, 200
    except ValueError as e:
        return {"error": str(e)}, 400


def modify_step(user, new_step_name, step_name=None, index=None, tasks=None):
    """Modify a step by name or index in the user's flow."""
    new_step = Step(new_step_name, tasks)
    try:
        user.modify_step(new_step, step_name=step_name, index=index)
        return {"status": f"Step modified to '{new_step_name}'"}, 200
    except ValueError as e:
        return {"error": str(e)}, 400

