"""Example configuration."""
JUSHUITAN_URL = "https://gyl.scm121.com"

DATABASE = {
    "path": "jushuitan.db",
}

WEB = {
    "host": "0.0.0.0",
    "port": 5000,
    "debug": True,
}

BROWSER = {
    "headless": True,
    "slow_mo": 100,
    "timeout": 30000,
}
