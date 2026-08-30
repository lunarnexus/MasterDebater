from .base import ConnectorError, require_fields, run_argv
from . import hermes, opencode, pi

REGISTRY = {
    hermes.NAME: hermes,
    pi.NAME: pi,
    opencode.NAME: opencode,
}


def call_connector(connector_name, config, prompt, timeout, verbose=False):
    connector = REGISTRY[connector_name]
    require_fields(config, connector.REQUIRED_FIELDS)
    argv = connector.build_argv(config, prompt)
    return run_argv(connector_name, argv, timeout, verbose)
