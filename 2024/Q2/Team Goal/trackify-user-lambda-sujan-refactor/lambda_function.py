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
