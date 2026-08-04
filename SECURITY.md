# Security Policy

## Supported versions

Security fixes are applied to the latest tagged release.

## Reporting

Do not open a public issue containing credentials, access tokens, HTTP response bodies, project data, or secret names that disclose internal systems. Report vulnerabilities privately through GitHub Security Advisories for this repository.

## Threat model

This plugin runs inside the Hermes process with the same operating-system privileges as Hermes. Installing a plugin is equivalent to installing trusted Python code.

The plugin protects against accidental persistence and common transport leaks. It does not provide process isolation from Hermes, its authorized subprocesses, a compromised host, a malicious plugin, or an operator with access to the process environment.

## Deployment requirements

- Use a dedicated Machine Identity per agent or deployment.
- Grant read-only access to only the required project and path.
- Use HTTPS with valid certificate verification.
- Keep `allow_insecure_http` disabled outside a trusted private network.
- Keep bootstrap credentials out of Git and protect their file with mode `600`.
- Rotate credentials after suspected exposure.
- Pin deployments to a reviewed release tag.

## Deliberate non-features

The source does not create, update, delete, or rotate Infisical secrets. It does not persist downloaded values or access tokens. Administrative tools, if ever added, must use separate permissions and an explicit approval boundary.
