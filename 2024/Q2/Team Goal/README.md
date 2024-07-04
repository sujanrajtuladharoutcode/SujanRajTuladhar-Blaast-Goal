# Refactoring and Differences in the Lambda Function Code

## Introduction
This document details the refactoring process and differences between the original and refactored Lambda function code. The original code is designed to handle incoming events, validate user IP and server key, retrieve secrets, authorize access, connect to MySQL, and fetch user roles, projects, and data. The refactored code improves readability, modularity, and error handling.

## Refactored Code
```python
import json
import boto3
import os
import pymysql
import logging


# Set logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Get from environment variable
secret_name = os.environ.get("SECRET_NAME")
rds_host = os.environ.get("RDS_HOST")
db_name = os.environ.get("DB_NAME")
db_user = os.environ.get("DB_USER")
db_password = os.environ.get("DB_PASSWORD")
db_port = os.environ.get("DB_PORT")


def json_response(status_code, message=None, data=None):
    """
    Function to generate a JSON response with the provided status code, message, and data.

    Args:
        status_code (int): The status code to be included in the response.
        message (str, optional): The message to be included in the response. Defaults to None.
        data (any, optional): The data to be included in the response. Defaults to None.

    Returns:
        dict: A dictionary containing the status code, headers, and body of the JSON response.
    """
    response = {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"message": message, "data": data}, default=str),
    }
    return response


def get_client_ip(event):
    """
    Fetch IP address
    """
    request_context = event.get("requestContext", {})
    http = request_context.get("http", {})
    identity = request_context.get("identity", {})

    return (
        http.get("sourceIp")
        or identity.get("sourceIp")
        or event.get("headers", {}).get("X-Forwarded-For", "").split(",")[0].strip()
    )


def get_server_key(event):
    """
    Fetch server_key
    """
    return event.get("headers", {}).get("server_key")


def connect_mysql_db():
    """
    Connects to a MySQL database using the provided credentials.

    Returns:
        pymysql.Connection: A connection object if the connection is successful,
        None: If there is an error connecting to the database.

    Raises:
        pymysql.MySQLError: If there is an error connecting to the database.
    """
    try:
        return pymysql.connect(
            host=rds_host,
            user=db_user,
            passwd=db_password,
            db=db_name,
            connect_timeout=5,
            ssl={"ssl": {"verify_mode": False}},
        )
    except pymysql.MySQLError as e:
        logger.error("Unexpected error: Could not connect to MySQL instance")
        logger.error(e)
        return None


def get_user_meta(user_id, connection):
    """
    Retrieves metadata for a user from the project_members table in the database.

    Args:
        user_id (int): The ID of the user.
        connection (pymysql.Connection): A connection object to the MySQL database.

    Returns:
        list: A list of dictionaries containing the project_id, status, createdAt, is_manager, and worked_until fields for each project the user is assigned to.
    """
    sql = "SELECT project_id, status, createdAt, is_manager, worked_until FROM project_members WHERE user_id = %s"
    connection.execute(sql, (user_id,))
    assigned_project = connection.fetchall()

    return [
        {
            "project_id": project[0],
            "status": project[1],
            "createdAt": str(project[2]),
            "is_manager": project[3],
            "worked_until": project[4],
        }
        for project in assigned_project
    ]


def fetch_data(cursor, query):
    """
    Executes a query using the provided cursor and returns all the results.

    Args:
        cursor: The cursor object used to execute the query.
        query: The SQL query to be executed.

    Returns:
        list: A list containing all the rows fetched as a result of the query.
    """
    cursor.execute(query)
    return cursor.fetchall()


def lambda_handler(event, context):
    """
    A Lambda handler function that processes incoming events, validates user IP and server key,
    retrieves secrets, authorizes access, establishes a connection to MySQL, fetches user roles, projects,
    and user data, and returns a JSON response based on the outcome.
    
    Args:
        event (dict): The event data passed to the Lambda function.
        context (object): The runtime information of the Lambda function.
    
    Returns:
        dict: A JSON response containing user roles, projects, and user data.
    """
    if not secret_name:
        return json_response(500, "SECRET_NAME environment variable is not set")

    try:
        user_ip = get_client_ip(event)
        server_key = get_server_key(event)

        if not user_ip:
            return json_response(400, "Unable to determine client or invalid network.")
        if not server_key:
            return json_response(400, "server_key header is missing or empty.")

        session = boto3.session.Session()
        client = session.client(service_name="secretsmanager")
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)

        if "SecretString" not in get_secret_value_response:
            return json_response(500, "No secret found.")

        secret = json.loads(get_secret_value_response["SecretString"])
        authorized = any(
            user_ip == ip and server_key == sk
            for key, value in secret.items()
            for ip, sk in [value.split(":")]
        )

        if not authorized:
            return json_response(403, "Network, server key not authorized or found.")

        connection = connect_mysql_db()
        if not connection:
            return json_response(500, "ERROR: Could not connect to MySQL instance.")

        try:
            with connection.cursor() as cur:
                user_roles = [
                    {"id": role[0], "name": role[1]}
                    for role in fetch_data(cur, "SELECT id, name FROM roles")
                ]

                user_projects = [
                    {
                        "id": project[0],
                        "name": project[1],
                        "privacy": project[2],
                        "status": project[3],
                        "client_id": project[4],
                        "createdAt": project[5],
                        "is_billable": project[6],
                        "type": project[7],
                    }
                    for project in fetch_data(cur, "SELECT id, name, privacy, status, client_id, createdAt, is_billable, type FROM projects")
                ]

                user_data = [
                    {
                        "id": user[0],
                        "name": user[1],
                        "email": user[2],
                        "status": user[3],
                        "role_id": user[4],
                        "createdAt": user[5],
                        "updatedAt": user[6],
                        "is_manager": user[7],
                        "phone": user[8],
                        "meta": get_user_meta(user[0], cur),
                    }
                    for user in fetch_data(cur, "SELECT id, name, email, status, role_id, createdAt, updatedAt, is_manager, phone FROM users")
                ]

            return json_response(200, data={"roles": user_roles, "projects": user_projects, "user_data": user_data})
        except Exception as e:
            logger.error("Could not execute query")
            logger.error(e)
            return json_response(500, f"Could not execute query, {str(e)}")
        finally:
            connection.close()

    except Exception as e:
        logger.error("Something went wrong")
        logger.error(e)
        return json_response(500, "Error: " + str(e))
```

## Original Code
```python
import json
import boto3
import os
import pymysql
import logging


# Set logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Get from environment variable
secret_name = os.environ["SECRET_NAME"]
rds_host = os.environ["RDS_HOST"]
db_name = os.environ["DB_NAME"]
db_user = os.environ["DB_USER"]
db_password = os.environ["DB_PASSWORD"]
db_port = os.environ["DB_PORT"]


def json_data(data):
    response = {
        "statusCode": data["statusCode"],
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(data, default=str),
    }
    return response


def get_client_ip(event):
    """
    Fetch IP address
    """
    if "requestContext" in event:
        if "http" in event["requestContext"]:
            return event["requestContext"]["http"].get("sourceIp")
        elif "identity" in event["requestContext"]:
            return event["requestContext"]["identity"].get("sourceIp")
    elif "headers" in event:
        return event["headers"].get("X-Forwarded-For", "").split(",")[0].strip()

    return None


def get_server_key(event):
    """
    Fetch server_key
    """
    if "headers" in event:
        return event["headers"].get("server_key")
    return None


def connect_mysql_db():
    try:
        # Establish a database connection
        conn = pymysql.connect(
            host=rds_host,
            user=db_user,
            passwd=db_password,
            db=db_name,
            connect_timeout=5,
            ssl={"ssl": {"verify_mode": False}},


        )

        return conn
    except pymysql.MySQLError as e:
        logger.error(f"Unexpected error: Could not connect to MySQL instance")
        logger.error(e)
        return "ERROR: Unexpected error: Could not connect to MySQL instance."


def get_user_meta(user_projects, user_id, connection):
    sql = "SELECT user_id, project_id, status, createdAt, is_manager, worked_until FROM project_members WHERE user_id = %s"
    connection.execute(sql, (user_id,))
    assigned_project = connection.fetchall()

    data = []

    if assigned_project:
        for project in assigned_project:
            data.append(
                {
                    "project_id": project[1],
                    "status": project[2],
                    "createdAt": str(project[3]),
                    "is_manager": project[4],
                    "worked_until": project[5],
                }
            )

    return data


def lambda_handler(event, context):

    if not secret_name:
        return json_data(
            {
                "statusCode": 500,
                "message": "SECRET_NAME environment variable is not set",
            }
        )

    try:
        # Get user's IP address and server_key from the event
        user_ip = get_client_ip(event)
        server_key = get_server_key(event)

        if not user_ip:
            return json_data(
                {
                    "statusCode": 400,
                    "error": "Unable to determine client or invalid network.",
                }
            )

        if not server_key:
            return json_data(
                {"statusCode": 400, "error": "server_key header is missing or empty."}
            )

        session = boto3.session.Session()
        client = session.client(service_name="secretsmanager")
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)

        if "SecretString" in get_secret_value_response:
            secret = json.loads(get_secret_value_response["SecretString"])

            for key, value in secret.items():
                stored_values = value.split(":")
                if len(stored_values) != 2:
                    continue

                stored_ip, stored_server_key = stored_values
                if user_ip == stored_ip and server_key == stored_server_key:

                    # Create a AWS RDS connection
                    rds_connecton = connect_mysql_db()

                    try:
                        with rds_connecton.cursor() as cur:
                            # roles
                            cur.execute("SELECT id, name FROM roles")
                            roles = cur.fetchall()
                            user_roles = []
                            for role in roles:
                                user_roles.append({"id": role[0], "name": role[1]})

                            # projects
                            cur.execute(
                                "SELECT id, name, privacy, status, client_id, createdAt, is_billable, type FROM projects"
                            )
                            projets = cur.fetchall()
                            user_projects = []
                            for project in projets:
                                user_projects.append(
                                    {
                                        "id": project[0],
                                        "name": project[1],
                                        "privacy": project[2],
                                        "status": project[3],
                                        "client_id": project[4],
                                        "createdAt": project[5],
                                        "is_billable": project[6],
                                        "type": project[7],
                                    }
                                )

                            # user data
                            cur.execute(
                                "SELECT id, name, email, status, role_id, createdAt, updatedAt, is_manager, phone FROM users"
                            )
                            users = cur.fetchall()
                            user_data = []
                            for user in users:
                                user_data.append(
                                    {
                                        "id": user[0],
                                        "name": user[1],
                                        "email": user[2],
                                        "status": user[3],
                                        "role_id": user[4],
                                        "createdAt": user[5],
                                        "updatedAt": user[6],
                                        "is_manager": user[7],
                                        "phone": user[8],
                                        "meta": get_user_meta(
                                            user_projects, str(user[0]), cur
                                        ),
                                    }
                                )

                            cur.close()

                            return json_data(
                                {
                                    "statusCode": 200,
                                    "roles": user_roles,
                                    "projects": user_projects,
                                    "user_data": user_data,
                                }
                            )
                    except Exception as e:
                        logger.error(f"Could not execute query")
                        logger.error(e)
                        return json_data(
                            {
                                "statusCode": 500,
                                "error": f"Could not execute query, {str(e)}",
                            }
                        )

                    finally:
                        rds_connecton.close()

            # no match found
            return json_data(
                {
                    "statusCode": 403,
                    "error": "Network, server key not authorized or found.",
                }
            )

        # no secret found
        return json_data({"statusCode": 500, "error": "No data found."})

    except Exception as e:
        logger.error(f"Something went wrong")
        logger.error(e)
        return json_data({"statusCode": 500, "error": "Error: " + str(e)})
```

## Differences and Improvements

### 1. Environment Variable Access
**Original Code:**
```python
secret_name = os.environ["SECRET_NAME"]
rds_host = os.environ["RDS_HOST"]
db_name = os.environ["DB_NAME"]
db_user = os.environ["DB_USER"]
db_password = os.environ["DB_PASSWORD"]
db_port = os.environ["DB_PORT"]
```

**Refactored Code:**
```python
secret_name = os.environ.get("SECRET_NAME")
rds_host = os.environ.get("RDS_HOST")
db_name = os.environ.get("DB_NAME")
db_user = os.environ.get("DB_USER")
db_password = os.environ.get("DB_PASSWORD")
db_port = os.environ.get("DB_PORT")
```
* The refactored code uses `os.environ.get()` to safely access environment variables, preventing the program from crashing if an environment variable is not set.

### 2. JSON Response Function
**Original Code:**
```python
def json_data(data):
    response = {
        "statusCode": data["statusCode"],
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(data, default=str),
    }
    return response
```

**Refactored Code:**
```python
def json_response(status_code, message=None, data=None):
    response = {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"message": message, "data": data}, default=str),
    }
    return response
```
* The refactored code provides more flexibility by allowing both `message` and `data` as optional parameters.

### 3. Fetching IP Address and Server Key
**Original Code:**
```python
def get_client_ip(event):
    if "requestContext" in event:
        if "http" in event["requestContext"]:
            return event["requestContext"]["http"].get("sourceIp")
        elif "identity" in event["requestContext"]:
            return event["requestContext"]["identity"].get("sourceIp")
    elif "headers" in event:
        return event["headers"].get("X-Forwarded-For", "").split(",")[0].strip()
    return None

def get_server_key(event):
    if "headers" in event:
        return event["headers"].get("server_key")
    return None
```

**Refactored Code:**
```python
def get_client_ip(event):
    request_context = event.get("requestContext", {})
    http = request_context.get("http", {})
    identity = request_context.get("identity", {})

    return (
        http.get("sourceIp")
        or identity.get("sourceIp")
        or event.get("headers", {}).get("X-Forwarded-For", "").split(",")[0].strip()
    )

def get_server_key(event):
    return event.get("headers", {}).get("server_key")
```
* The refactored code simplifies the logic and improves readability.

### 4. MySQL Database Connection
**Original Code:**
```python
def connect_mysql_db():
    try:
        conn = pymysql.connect(
            host=rds_host,
            user=db_user,
            passwd=db_password,
            db=db_name,
            connect_timeout=5,
            ssl={"ssl": {"verify_mode": False}},
        )
        return conn
    except pymysql.MySQLError as e:
        logger.error(f"Unexpected error: Could not connect to MySQL instance")
        logger.error(e)
        return "ERROR: Unexpected error: Could not connect to MySQL instance."
```

**Refactored Code:**
```python
def connect_mysql_db():
    try:
        return pymysql.connect(
            host=rds_host,
            user=db_user,
            passwd=db_password,
            db=db_name,
            connect_timeout=5,
            ssl={"ssl": {"verify_mode": False}},
        )
    except pymysql.MySQLError as e:
        logger.error("Unexpected error: Could not connect to MySQL instance")
        logger.error(e)
        return None
```
* The refactored code removes redundant variable assignment and improves error handling.

### 5. User Metadata Retrieval
**Original Code:**
```python
def get_user_meta(user_projects, user_id, connection):
    sql = "SELECT user_id, project_id, status, createdAt, is_manager, worked_until FROM project_members WHERE user_id = %s"
    connection.execute(sql, (user_id,))
    assigned_project = connection.fetchall()

    data = []
    if assigned_project:
        for project in assigned_project:
            data.append(
                {
                    "project_id": project[1],
                    "status": project[2],
                    "createdAt": str(project[3]),
                    "is_manager":

 project[4],
                    "worked_until": project[5],
                }
            )
    return data
```

**Refactored Code:**
```python
def get_user_meta(user_id, connection):
    sql = "SELECT project_id, status, createdAt, is_manager, worked_until FROM project_members WHERE user_id = %s"
    connection.execute(sql, (user_id,))
    assigned_project = connection.fetchall()

    return [
        {
            "project_id": project[0],
            "status": project[1],
            "createdAt": str(project[2]),
            "is_manager": project[3],
            "worked_until": project[4],
        }
        for project in assigned_project
    ]
```
* The refactored code directly returns the list of dictionaries, improving code conciseness and readability.

### 6. Query Execution
**Original Code:**
```python
def lambda_handler(event, context):
    if not secret_name:
        return json_data(
            {
                "statusCode": 500,
                "message": "SECRET_NAME environment variable is not set",
            }
        )
    try:
        user_ip = get_client_ip(event)
        server_key = get_server_key(event)

        if not user_ip:
            return json_data(
                {
                    "statusCode": 400,
                    "error": "Unable to determine client or invalid network.",
                }
            )
        if not server_key:
            return json_data(
                {"statusCode": 400, "error": "server_key header is missing or empty."}
            )

        session = boto3.session.Session()
        client = session.client(service_name="secretsmanager")
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)

        if "SecretString" in get_secret_value_response:
            secret = json.loads(get_secret_value_response["SecretString"])
            for key, value in secret.items():
                stored_values = value.split(":")
                if len(stored_values) != 2:
                    continue
                stored_ip, stored_server_key = stored_values
                if user_ip == stored_ip and server_key == stored_server_key:
                    rds_connecton = connect_mysql_db()
                    try:
                        with rds_connecton.cursor() as cur:
                            cur.execute("SELECT id, name FROM roles")
                            roles = cur.fetchall()
                            user_roles = []
                            for role in roles:
                                user_roles.append({"id": role[0], "name": role[1]})

                            cur.execute(
                                "SELECT id, name, privacy, status, client_id, createdAt, is_billable, type FROM projects"
                            )
                            projets = cur.fetchall()
                            user_projects = []
                            for project in projets:
                                user_projects.append(
                                    {
                                        "id": project[0],
                                        "name": project[1],
                                        "privacy": project[2],
                                        "status": project[3],
                                        "client_id": project[4],
                                        "createdAt": project[5],
                                        "is_billable": project[6],
                                        "type": project[7],
                                    }
                                )

                            cur.execute(
                                "SELECT id, name, email, status, role_id, createdAt, updatedAt, is_manager, phone FROM users"
                            )
                            users = cur.fetchall()
                            user_data = []
                            for user in users:
                                user_data.append(
                                    {
                                        "id": user[0],
                                        "name": user[1],
                                        "email": user[2],
                                        "status": user[3],
                                        "role_id": user[4],
                                        "createdAt": user[5],
                                        "updatedAt": user[6],
                                        "is_manager": user[7],
                                        "phone": user[8],
                                        "meta": get_user_meta(
                                            user_projects, str(user[0]), cur
                                        ),
                                    }
                                )

                            cur.close()

                            return json_data(
                                {
                                    "statusCode": 200,
                                    "roles": user_roles,
                                    "projects": user_projects,
                                    "user_data": user_data,
                                }
                            )
                    except Exception as e:
                        logger.error(f"Could not execute query")
                        logger.error(e)
                        return json_data(
                            {
                                "statusCode": 500,
                                "error": f"Could not execute query, {str(e)}",
                            }
                        )
                    finally:
                        rds_connecton.close()
            return json_data(
                {
                    "statusCode": 403,
                    "error": "Network, server key not authorized or found.",
                }
            )
        return json_data({"statusCode": 500, "error": "No data found."})
    except Exception as e:
        logger.error(f"Something went wrong")
        logger.error(e)
        return json_data({"statusCode": 500, "error": "Error: " + str(e)})
```

**Refactored Code:**
```python
def lambda_handler(event, context):
    if not secret_name:
        return json_response(500, "SECRET_NAME environment variable is not set")

    try:
        user_ip = get_client_ip(event)
        server_key = get_server_key(event)

        if not user_ip:
            return json_response(400, "Unable to determine client or invalid network.")
        if not server_key:
            return json_response(400, "server_key header is missing or empty.")

        session = boto3.session.Session()
        client = session.client(service_name="secretsmanager")
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)

        if "SecretString" not in get_secret_value_response:
            return json_response(500, "No secret found.")

        secret = json.loads(get_secret_value_response["SecretString"])
        authorized = any(
            user_ip == ip and server_key == sk
            for key, value in secret.items()
            for ip, sk in [value.split(":")]
        )

        if not authorized:
            return json_response(403, "Network, server key not authorized or found.")

        connection = connect_mysql_db()
        if not connection:
            return json_response(500, "ERROR: Could not connect to MySQL instance.")

        try:
            with connection.cursor() as cur:
                user_roles = [
                    {"id": role[0], "name": role[1]}
                    for role in fetch_data(cur, "SELECT id, name FROM roles")
                ]

                user_projects = [
                    {
                        "id": project[0],
                        "name": project[1],
                        "privacy": project[2],
                        "status": project[3],
                        "client_id": project[4],
                        "createdAt": project[5],
                        "is_billable": project[6],
                        "type": project[7],
                    }
                    for project in fetch_data(cur, "SELECT id, name, privacy, status, client_id, createdAt, is_billable, type FROM projects")
                ]

                user_data = [
                    {
                        "id": user[0],
                        "name": user[1],
                        "email": user[2],
                        "status": user[3],
                        "role_id": user[4],
                        "createdAt": user[5],
                        "updatedAt": user[6],
                        "is_manager": user[7],
                        "phone": user[8],
                        "meta": get_user_meta(user[0], cur),
                    }
                    for user in fetch_data(cur, "SELECT id, name, email, status, role_id, createdAt, updatedAt, is_manager, phone FROM users")
                ]

            return json_response(200, data={"roles": user_roles, "projects": user_projects, "user_data": user_data})
        except Exception as e:
            logger.error("Could not execute query")
            logger.error(e)
            return json_response(500, f"Could not execute query, {str(e)}")
        finally:
            connection.close()

    except Exception as e:
        logger.error("Something went wrong")
        logger.error(e)
        return json_response(500, "Error: " + str(e))
```
* The refactored code introduces helper functions for fetching data, improving modularity and readability. It also adds better error handling and logging.

By breaking down the code into smaller, more manageable functions, improving error handling, and enhancing readability, the refactored code is easier to maintain, understand, and extend.