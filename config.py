from configparser import ConfigParser, Error as ConfigError


def read_config(input_path: str) -> ConfigParser:
    try:
        cfg = ConfigParser()
        cfg.read(input_path)
        return cfg
    except ConfigError as c:
        raise RuntimeError("Error reading config file: %s" % c)
