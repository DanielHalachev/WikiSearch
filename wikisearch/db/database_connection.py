import logging

from mysql.connector import pooling


class DatabaseConnectionService:
    def __init__(self, config):
        self.logger = logging.getLogger(__name__)
        self.logger.debug(
            "Initializing DatabaseConnectionService with config: %s", config)
        self.pool = pooling.MySQLConnectionPool(
            pool_name="pool",
            pool_size=10,
            **config
        )

    def get_connection(self):
        self.logger.debug("Getting a connection from the pool")
        return self.pool.get_connection()

    def __enter__(self):
        self.logger.debug("Entering context and getting a connection")
        self.connection = self.get_connection()
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.debug("Exiting context and closing the connection")
        self.connection.close()
        if exc_type:
            self.logger.error("Exception occurred: %s", exc_val)
