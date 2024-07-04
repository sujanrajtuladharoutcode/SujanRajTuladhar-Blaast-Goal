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
