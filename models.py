from enum import Enum

class Status(Enum):
    COMPLETED = "completed"
    NOT_COMPLETED = "not completed"
    IN_PROGRESS = "in progress"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

class User:
    def __init__(self, user_id, email):
        self.user_id = user_id
        self.email = email
        self.steps = []  # A list of steps that the user must complete
        self.status = Status.IN_PROGRESS
        self.current_step_index = 0
        self.steps_names = set()

    def add_step(self, step, index=None):
        """Add a step at the specified index or at the end if no index is provided."""
        if index is None:
            self.steps.append(step)
        elif 0 <= index <= len(self.steps):
            self.steps.insert(index, step)
        else:
            raise IndexError(
                "Index out of range. Must be between 0 and the number of existing steps.")
        self.steps_names.add(step.step_name)

    def remove_step(self, step_name=None, index=None):
        """Remove a step by name or index."""
        if index is not None:
            if 0 <= index < len(self.steps):
                self.steps_names.remove(self.steps[index].step_name)
                return self.steps.pop(index)
            else:
                raise ValueError("Index out of range")
        elif step_name:
            for i, step in enumerate(self.steps):
                if step.step_name == step_name:
                    self.steps_names.remove(step_name)
                    return self.steps.pop(i)
            raise ValueError(f"Step with name '{step_name}' not found")
        else:
            raise ValueError("Either step_name or index must be provided")

    def modify_step(self, new_step, step_name=None, index=None):
        """Modify a step by name or index."""
        if index is not None and 0 <= index < len(self.steps):
            self.steps_names.remove(self.steps[index].step_name)
            self.steps[index] = new_step
        elif step_name:
            for i, step in enumerate(self.steps):
                if step.step_name == step_name:
                    self.steps[i] = new_step
                    self.steps_names.remove(step_name)
                    self.steps_names.add(new_step.step_name)
                    return
            raise ValueError(f"Step with name '{step_name}' not found")
        else:
            raise ValueError("Either step_name or index must be provided")
        self.steps_names.add(new_step.step_name)


class Step:
    def __init__(self, step_name, tasks=None):
        self.step_name = step_name
        self.tasks = tasks if tasks else [Task(step_name)]
        self.status = Status.NOT_COMPLETED
        self.current_task_index = 0
        self.tasks_names = {task.task_name for task in self.tasks}


class Task:
    def __init__(self, task_name, condition=None, required_fields=None):
        self.task_name = task_name
        self.status = Status.NOT_COMPLETED
        self.condition = condition  # Condition can be a callable (e.g., IQ score condition)
        self.required_fields = required_fields if required_fields else []

    def check_completion(self, condition_var):
        """Check if the task is completed based on the condition."""
        if not self.condition(condition_var):
            self.status = Status.REJECTED
        else:
            self.status = Status.COMPLETED