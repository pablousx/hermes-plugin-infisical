"""Hermes plugin entry point for the Infisical SecretSource."""

if __package__:
    from .infisical_source import InfisicalSource
else:  # direct checkout import used by pytest
    from infisical_source import InfisicalSource


def register(ctx):
    """Register the read-only Infisical secret source."""
    ctx.register_secret_source(InfisicalSource())


__all__ = ["register"]
