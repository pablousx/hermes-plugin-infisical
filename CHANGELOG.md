# Changelog

All notable changes follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed

- Expanded the README and install prompt with end-to-end Universal Auth setup,
  least-privilege project access, credential retrieval, and safe Hermes storage
  instructions.
- Added Infisical setup guidance and documentation links to Hermes' interactive
  `requires_env` prompts.
- Added a safe debugging prompt covering plugin discovery, bootstrap, configuration,
  authentication, authorization, network, precedence, and startup-timing failures.
- Clarified the exact profile-scoped `.env` destination for the Universal Auth
  Client ID and Client Secret, including the `hermes config env-path` lookup.

## [0.1.0] - 2026-08-04

### Added

- Read-only bulk `SecretSource` for Infisical Universal Auth.
- Single project, environment, and path configuration.
- TLS enforcement with explicit private-network HTTP opt-in.
- Sanitized error mapping, response-size cap, and same-origin redirects.
- Bootstrap variable protection and Hermes provenance support.
- Unit, security, conformance, plugin-loader smoke, and optional E2E tests.
