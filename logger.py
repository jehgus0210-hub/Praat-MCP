import logging


class Logger:
    """
    
    """
    def __init__(self, name: str = "praat-mcp"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        self.handler = logging.StreamHandler()  # stderr
        self.handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

        self.logger.handlers.clear()
        self.logger.addHandler(self.handler)

    def info(self, payload: str, *arg):
        self.logger.info(payload.format(arg))

    def warning(self, payload: str, *arg):
        self.logger.warning(payload.format(arg))

    def error(self, payload: str, *arg):
        self.logger.error(payload.format(arg))
