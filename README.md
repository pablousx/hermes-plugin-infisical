# Hermes Infisical Plugin

A read-only [Hermes Agent](https://github.com/NousResearch/hermes-agent) `SecretSource` that loads environment-shaped secrets from [Infisical](https://infisical.com/) using Universal Auth.

- No Hermes fork or core patch.
- No Infisical SDK or runtime dependency.
- No downloaded secret is written to `.env`, config, cache, or logs.
- Hermes keeps control of precedence, protected variables, and provenance.

## Requirements

- Hermes Agent with SecretSource API v1. Verified with Hermes `v0.19.1` and checkout `4a8eeb5d1`.
- Python 3.11+.
- An Infisical Machine Identity configured for Universal Auth.
- Read access to the selected project, environment, and path.

## Install with a prompt

Paste this prompt into a Hermes agent. Replace the placeholders first. The agent should install the plugin, configure it, verify it without exposing values, and retain the operational rules for future credential use.

```text
Install and configure the read-only Infisical SecretSource plugin for this Hermes profile.

Plugin repository: pablousx/hermes-plugin-infisical
Infisical project ID: <PROJECT_ID>
Environment: <ENVIRONMENT, usually prod>
Secret path: <SECRET_PATH, for example /hermes>
Recursive: <true or false>

Instructions:
1. Read the repository README, SECURITY.md, plugin.yaml, and the installed Hermes
   SecretSource/plugin documentation before changing configuration.
2. Install it with:
   hermes plugins install pablousx/hermes-plugin-infisical --enable
3. Configure secrets.sources and secrets.infisical for the values above. Preserve
   INFISICAL_HOST_URL, INFISICAL_UNIVERSAL_AUTH_CLIENT_ID, and
   INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET.
4. Use only the three bootstrap variables for Universal Auth. If any are missing,
   ask me for them or retrieve them from the approved secret bootstrap location.
   Never print, log, echo, commit, or include their values in tool output.
5. Keep HTTPS required. Do not enable allow_insecure_http unless I explicitly say
   this is a trusted private network.
6. Restart the gateway and verify with `hermes secrets status`. Report only source
   status, provenance, counts, and variable names when necessary. Never dump values
   or the complete process environment.
7. Run a safe smoke test proving that at least one expected credential is attributed
   to Infisical. Do not persist downloaded values to .env or config.yaml.
8. From now on, when a task needs a credential supplied by this source, use the
   environment variable normally. Do not fetch or display the raw value. If it is
   missing, report the variable name and Infisical source status instead of asking
   me to paste the secret into chat.
9. Treat this plugin as read-only. Do not create, update, delete, or rotate Infisical
   secrets through it.
10. Account for Hermes' first-process plugin timing limitation documented in the
    README. Keep credentials required by the initial gateway process in the approved
    bootstrap source until Hermes resolves that limitation.

Finish by reporting the installed plugin version, configuration scope, test result,
and any first-process credentials that could not be migrated. Do not report values.
```

## Install

```bash
hermes plugins install pablousx/hermes-plugin-infisical --enable
hermes gateway restart
```

Hermes currently clones the repository default branch. To pin a reviewed release after installation:

```bash
PLUGIN_DIR="${HERMES_HOME:-$HOME/.hermes}/plugins/infisical"
git -C "$PLUGIN_DIR" fetch --tags
git -C "$PLUGIN_DIR" checkout v0.1.0
hermes gateway restart
```

The installer places the plugin under `$HERMES_HOME/plugins/infisical/`.

## Bootstrap environment

Hermes needs three values before it can reach Infisical:

```env
INFISICAL_HOST_URL=https://infisical.example.com
INFISICAL_UNIVERSAL_AUTH_CLIENT_ID=...
INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET=...
```

Keep this bootstrap identity local, out of Git, and protect the containing file with mode `600`. Use a separate read-only Machine Identity per agent or deployment.

## Hermes configuration

Add the source to `config.yaml`:

```yaml
plugins:
  enabled:
    - infisical

secrets:
  sources:
    - infisical
  preserve_existing:
    - INFISICAL_HOST_URL
    - INFISICAL_UNIVERSAL_AUTH_CLIENT_ID
    - INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET
  infisical:
    enabled: true
    project_id: "YOUR-INFISICAL-PROJECT-ID"
    environment: "prod"
    secret_path: "/hermes"
    recursive: false
    override_existing: true
    timeout_seconds: 30
```

Infisical secret names must be valid environment variable names such as `OPENAI_API_KEY`. Invalid, empty, malformed, and duplicate entries are skipped with warnings that never contain values.

### Options

| Setting | Default | Meaning |
|---|---:|---|
| `project_id` | required | Infisical project/workspace ID |
| `environment` | `prod` | Infisical environment slug |
| `secret_path` | `/` | Folder to load |
| `recursive` | `false` | Request child-folder secrets |
| `override_existing` | `true` | Let Infisical replace matching shell/`.env` values |
| `timeout_seconds` | Hermes default | Wall-clock fetch timeout enforced by Hermes |
| `allow_insecure_http` | `false` | Permit HTTP for a trusted private network |

`allow_insecure_http` sends credentials and secrets without TLS. Do not use it over public or untrusted networks.

## Verify safely

```bash
hermes secrets status
```

After restart, credential status output should attribute applied values to `Infisical`. Do not print the environment or run commands that expose values.

## Important Hermes startup limitation

Hermes `v0.19.1` discovers external plugins after the first `load_hermes_dotenv()` call in the process that discovers them. Therefore:

- The source is available to subsequently spawned gateway children, cron sessions, subagents, and explicit secret-source refreshes.
- Credentials required by the first gateway process itself may still need to remain in the local bootstrap environment.
- Installing the plugin does not currently guarantee that a first-process Telegram token or provider key can come from this external source.

This behavior is in Hermes' plugin contract, not this plugin. The plugin does not patch Hermes. Re-test it when upgrading Hermes.

## Precedence

The plugin returns a bulk mapping. Hermes decides what gets applied:

1. `secrets.preserve_existing` values win.
2. Existing environment values win unless `override_existing: true`.
3. Mapped sources outrank bulk sources.
4. Among sources of equal shape, the first configured source wins.

The Infisical bootstrap variables are protected and cannot be overwritten by this or another source.

## Security model

The plugin improves central management, revocation, and rotation, but it does not hide secrets from the Hermes process. Values exist in process memory and may be passed to authorized child processes just like other Hermes credentials.

The plugin:

- performs only Universal Auth login and secret reads;
- does not expose write, delete, or rotate tools;
- verifies TLS by default;
- rejects cross-origin HTTP redirects;
- caps JSON responses at 2 MiB;
- never includes HTTP response bodies in errors;
- never caches tokens or downloaded secrets on disk.

See [SECURITY.md](SECURITY.md).

## Test

Against a local Hermes checkout:

```bash
HERMES_AGENT_REPO="$HOME/.hermes/hermes-agent" \
PYTHONPATH="$HOME/.hermes/hermes-agent" \
"$HOME/.hermes/hermes-agent/venv/bin/python" -m pytest -q

"$HOME/.hermes/hermes-agent/venv/bin/python" -m ruff check .
```

Optional live E2E:

```bash
export INFISICAL_E2E_PROJECT_ID="..."
export INFISICAL_E2E_ENVIRONMENT="prod"
export INFISICAL_E2E_SECRET_PATH="/tests/hermes-plugin"
export INFISICAL_E2E_EXPECTED_COUNT="2" # optional
python -m pytest -q -m e2e
```

Use a dedicated read-only identity and test path. The test asserts counts and provenance without printing values.

## Uninstall and revoke

```bash
hermes plugins disable infisical
hermes plugins uninstall infisical
hermes gateway restart
```

Then revoke the Machine Identity or its Universal Auth client secret in Infisical.

## Scope

Version 0.1 supports one project, one environment, and one path per Hermes profile. Multi-project loading, references such as `infisical://...`, mid-session refresh, and administrative write tools are intentionally out of scope.

## License

MIT
