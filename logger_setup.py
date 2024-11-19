
import logging
import logging.config


def setup_logging(log_file: str = "app.log"):
    """
    Configures the logging settings for the application.

    This function sets up logging for both file and console outputs. It configures the log level
    to DEBUG, meaning that all messages at the DEBUG level and higher (INFO, WARNING, ERROR, CRITICAL)
    will be logged. The log messages are formatted to include the timestamp, log level, module name,
    and message content.

    Args:
        log_file (str): The filename for the log file where logs will be stored.
                        Defaults to "app.log" if not provided.

    Returns:
        logging.Logger: A configured logger instance.

    Example:
        logger = setup_logging("my_log_file.log")
        logger.info("This is an info log.")
        logger.error("This is an error log.")

    The function sets up two handlers:
        1. **FileHandler**: Writes log messages to the specified log file.
        2. **StreamHandler**: Writes log messages to the console (stdout).

    Both handlers are configured to log messages of level DEBUG or higher, and use the same formatter.
    """

    # Configuration dictionary for logging
    logging_config = {
        "version": 1,  # Version of the logging configuration format
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
                # Log format
            },
        },
        "handlers": {
            # Handler for logging to a file
            "file": {
                "class": "logging.FileHandler",
                # Specifies the use of FileHandler
                "filename": log_file,  # Specifies the log file's name
                "formatter": "default",  # Use the default formatter
                "level": "INFO",
            },
            # Handler for logging to the console (stdout)
            "console": {
                "class": "logging.StreamHandler",
                # Specifies the use of StreamHandler (console)
                "formatter": "default",  # Use the default formatter
                "level": "INFO",
            },
        },
        "root": {
            "level": "INFO",
            "handlers": ["file", "console"],
            # Both file and console handlers are used
        },
    }

    # Apply the logging configuration to the logging module
    logging.config.dictConfig(logging_config)

    # Return the logger instance that is now configured
    return logging.getLogger()
