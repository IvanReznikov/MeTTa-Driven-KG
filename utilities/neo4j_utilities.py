from neo4j import GraphDatabase, basic_auth
import yaml, time
from py2neo import Graph
from utilities import read_load_file_utilities
import asyncio
from concurrent.futures import ThreadPoolExecutor


class DatabaseManager:
    """Manages database connections to Neo4j."""

    def __init__(self, neo4j_username, neo4j_pass, connection_uri):
        """Initializes the database manager with connection configuration.

        Args:
            file_path: Path to the YAML file containing connection details.
        """

        self.driver = GraphDatabase.driver(
            connection_uri,
            auth=basic_auth(neo4j_username, neo4j_pass),
        )

        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1")
                for record in result:
                    print(f"Server is accessible, returned: {record[0]}")

        except Exception as e:
            print(f"Could not connect to Neo4j, error: {e}")
            self.close()

    def close(self):
        self.driver.close()

    def verify_connection(
        self, database_name: str, attempts: int = 5, initial_delay: float = 0.5
    ):
        """Verifies the connection to a specific database with a set number of attempts.

        Args:
            database_name: The name of the database to connect to.
            attempts: The number of connection attempts before giving up.
            initial_delay: The initial delay between attempts, which increases exponentially.
        """
        for attempt in range(attempts):
            try:
                with self.driver.session(database=database_name) as session:
                    result = session.run("MATCH (n) Return n LIMIT 1")
                    for record in result:
                        print(f"Server is accessible, returned: {record[0]}")
                    return
            except Exception as e:
                print(
                    f"Attempt {attempt + 1} for database '{database_name}': Could not connect, waiting... Error: {e}"
                )
                time_to_wait = initial_delay * (2**attempt)
                time.sleep(time_to_wait)

        print(
            f"Failed to connect to the database '{database_name}' after several attempts."
        )

    def create_database_if_not_exists(self, database_name: str):
        """Creates a database if it does not already exist.

        Args:
            database_name: The name of the database to create.
        """

        with self.driver.session(database="system") as session:
            query = f"CREATE DATABASE {database_name} IF NOT EXISTS"
            session.run(query)


def connect_to_custom_db(
    NAME_DATABASE: str, connection_uri: str, neo_user: str, neo_pass: str
):
    """Connects to a custom Neo4j database using Py2Neo.

    Args:
        file_path: Path to the YAML file containing connection details.
        NAME_DATABASE: The name of the database to connect to.

    Returns:
        A `Graph` object from Py2Neo, representing the database connection.
    """
    graph = Graph(
        connection_uri,
        name=NAME_DATABASE,
        auth=(neo_user, neo_pass),
    )
    return graph


def clear_neo4j_db(graph: Graph):
    # This function takes a Graph object and executes a Cypher query
    # to delete all nodes and relationships in the database, effectively clearing it.
    graph.run(
        """MATCH (n) 
            DETACH DELETE n"""  # Detach and delete all matched nodes
    )


def open_ssh_tunnel(
    config_connection,
):
    # Define the SSH tunnel configuration
    server = SSHTunnelForwarder(
        (config_connection["ssh_host"], 22),  # SSH хост и порт
        ssh_username=config_connection["ssh_username"],
        ssh_password=config_connection["ssh_password"],
        remote_bind_address=(
            config_connection["neo4j_host"],
            config_connection["neo4j_port"],
        ),  # Адрес и порт Neo4j на удалённом сервере
    )

    # Start the SSH tunnel
    server.start()
    return server


def wrapper_verify_connection(
    server: DatabaseManager,
    database_name: str = "neo4j",
    neo_username="",
    neo_pass="",
    connection_uri="",
):
    # If the server is successfully initialized, proceed to check if the database exists.
    # If it does not, the database will be created.
    server.create_database_if_not_exists(database_name=database_name)

    # Verify the connection to the specified database to ensure it's ready for operations.
    # if not ssh_mode:
    server.verify_connection(database_name=database_name)
    # After operations are complete, close the server connection as a cleanup step.
    server.close()

    # Establish and return a connection to the specified database using a custom method.
    # This method also utilizes the same configuration file for connection details.

    # connection_config = read_load_file_utilities.safe_read_yaml(file_path=r"config/connection_to_local_neo.yaml")
    # ssh_tunnel = open_ssh_tunnel(connection_config)
    graph_server = connect_to_custom_db(
        NAME_DATABASE=database_name,  # The name of the database to connect to.
        connection_uri=connection_uri,
        neo_user=neo_username,
        neo_pass=neo_pass,
    )
    return graph_server  # Return the Graph object connected to the specified database.
    # graph_server = connect_to_custom_db(
    #         file_path=r"config/connection_to_local_neo.yaml",  # Configuration file path.
    #         NAME_DATABASE=database_name,  # The name of the database to connect to.
    #         connection_uri=f"bolt://localhost:{ssh_tunnel.local_bind_port}"
    #     )
    # return (
    #         graph_server  # Return the Graph object connected to the specified database.
    #     )


def wrapper_connection_to_neo4j_database(
    DATABASE_NAME, ssh_mode=False, neo4j_username="", neo4j_pass="", connection_uri=""
):
    # This function establishes a connection to a Neo4j database.
    # It takes the name of the database as input.

    # Initialize the DatabaseManager with the configuration file path.
    # This manager handles database operations such as creation and verification.
    connection_config = read_load_file_utilities.safe_read_yaml(
        file_path=r"config/connection_to_local_neo.yaml"
    )
    if ssh_mode:
        ...
        ssh_tunnel = open_ssh_tunnel(config_connection=connection_config)
        print("SSH tunnel established")
        if not neo4j_pass:
            neo4j_pass = connection_config["neo4j_password_ssh"]
        if not neo4j_username:
            neo4j_username = connection_config["neo4j_username_ssh"]
        if not connection_uri:
            connection_uri = f"bolt://localhost:{ssh_tunnel.local_bind_port}"

    else:
        if not neo4j_pass:
            neo4j_pass = connection_config["password"]
        if not neo4j_username:
            neo4j_username = connection_config["user"]
        if not connection_uri:
            connection_uri = connection_config["uri"]

    print("=" * 50)
    print(connection_config)
    print("-" * 50)

    server = DatabaseManager(
        connection_uri=connection_uri,
        neo4j_pass=neo4j_pass,
        neo4j_username=neo4j_username,
    )
    return wrapper_verify_connection(
        server=server,
        database_name=DATABASE_NAME,
        neo_pass=neo4j_pass,
        connection_uri=connection_uri,
        neo_username=neo4j_username,
    )


async def run_query_async(graph_server, query, package):
    loop = asyncio.get_event_loop()

    with ThreadPoolExecutor() as pool:
        result = await loop.run_in_executor(
            pool, graph_server.run, query, {"relationships": package}
        )

        return result
