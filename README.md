# Admissions Flow Application
 
This application manages the admissions flow for users, including steps and tasks that need to be completed. It is built using Flask and provides various endpoints to interact with the flow.
 
## Installation
 
1. Clone the repository:
    ```sh
    git clone <repository-url>
    cd <repository-directory>
   ```

2. Install the required packages:
    
```Shell
    pip install -r requirements.txt
 ```
3. Run the application:
    
``` Shell
    flask run
 ```   
 
## Endpoints
 
### Create User
 
* Endpoint: POST /users

Request Body:
```JSON
{
    "email": "user@example.com"
}
``` 
Response:

```JSON
{
    "user_id": "generated-user-id"
}
```
 
### Get User Flow
 
Endpoint: GET /users/<user_id>/flow

Response:
```JSON
{
    "flow": [
        {
            "step_name": "Personal Details Form",
            "index": 0,
            "status": "Not Completed"
        }
    ]
}
```
 
### Get Current Step and Task
 
Endpoint: GET /users/<user_id>/current_step 

Response:
```JSON
{
    "current_step": {
        "name": "Personal Details Form",
        "level": 0,
        "status": "Not Completed"
    },
    "current_task": {
        "name": "Personal Details Form",
        "status": "Not Completed"
    }
}
``` 
### Complete Task
 
Endpoint: PUT /users/<user_id>/steps/<step_name>/tasks/<task_name>

Request Body:
```JSON
{
    "task_payload": {
        "field1": "value1",
        "field2": "value2"
    }
}
``` 

Response:
```JSON
{
    "status": "Task marked as completed"
}
``` 
### Complete Step
 
Endpoint: PUT /users/<user_id>/complete_step/<step_name>

Request Body:
```JSON
{
    "step_payload": {
        "task1": {
            "field1": "value1",
            "field2": "value2"
        }
    }
}
``` 

Response:
```JSON
{
    "status": "Step marked as completed"
}
``` 
### Get User Status
 
Endpoint: GET /users/<user_id>/status 

Response:
```JSON
{
    "status": "In Progress"
}
``` 
### Add Step
 
Endpoint: POST /users/<user_id>/add_step
 
Request Body (index and condition are optional):
```JSON
{
    "step_name": "New Step",
    "index": 1,  
    "tasks": [
        {
            "task_name": "New Task",
            "required_fields": ["field1", "field2"],
            "condition": "condition_function"  
        }
    ]
}
``` 
Response:
```JSON
{
    "status": "Step 'New Step' added"
}
``` 
### Remove Step
 
Endpoint: DELETE /users/<user_id>/remove_step
 
Request Body (specify one of step_name or index):
```JSON
{
    "step_name": "Step to Remove",  
    "index": 1  
}
``` 
Response:
```JSON
{
    "status": "Step removed successfully"
}
``` 
### Modify Step
 
Endpoint: PUT /users/<user_id>/modify_step
 
Request Body (specify one of step_name or index, condition is optional)):
```JSON
{
    "new_step_name": "Modified Step",
    "step_name": "Step to Modify",  
    "index": 1, 
    "tasks": [
        {
            "task_name": "Modified Task",
            "required_fields": ["field1", "field2"],
            "condition": "condition_function"  
        }
    ]
}
``` 
Response:
```JSON
{
    "status": "Step modified to 'Modified Step'"
}
``` 
### Update User Email
 
Endpoint: PATCH /users/<user_id>/update_email
 
Request Body:
```JSON
{
    "email": "new-email@example.com"
}
``` 
Response:
```JSON
{
    "status": "Email updated successfully"
}
``` 
### Delete User
 
Endpoint: DELETE /users/<user_id>
 
Response:
```JSON
{
    "status": "User deleted"
}
``` 
### Get All Users
 
Endpoint: GET /users
 
Response:
```JSON
{
    "users": [
        {
            "user_id": "user-id",
            "email": "user@example.com"
        }
    ]
}
```
## Step Requirements for Completing Each Step
Below is an explanation of the requirements to complete each step in the admissions flow.

### Personal Details Form
* Endpoint: POST /users/<user_id>/steps/Personal Details Form
* Required Fields:
  * first_name
  * last_name
  * email
  * timestamp
### IQ Test
* Endpoint: POST /users/<user_id>/steps/IQ Test
* Required Fields:
  * test_id
  * score
  * timestamp
  * condition_var (The field to check the condition on)
### Interview
* Endpoint: POST /users/<user_id>/steps/Interview
* Required Fields:
  * For schedule interview: 
    * interview_date
  * For perform interview: 
    * interview_date 
    * interviewer_id
    * decision
    * condition_var (The field to check the condition on)
### Sign Contract
* Endpoint: POST /users/<user_id>/steps/Sign Contract
* Required Fields:
  * For upload identification document: 
    * passport_number
    * timestamp
  * For sign contract: 
    * timestamp
### Payment
* Endpoint: POST /users/<user_id>/steps/Payment 
* Required Fields:
  * payment_id
  * timestamp
### Join Slack
* Endpoint: POST /users/<user_id>/steps/Join Slack
* Required Fields:
  * email 
  * timestamp
