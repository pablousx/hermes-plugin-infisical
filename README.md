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

## Where the Client ID and Client Secret go

Both credentials go in the `.env` file of the Hermes profile that runs the plugin. They do **not** go in `config.yaml`, the plugin repository, the agent prompt, or the Infisical project folder.

| Credential | Hermes `.env` entry |
|---|---|
| Infisical Client ID | `INFISICAL_UNIVERSAL_AUTH_CLIENT_ID=...` |
| Infisical Client Secret | `INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET=...` |

Use Hermes to print the exact file path for the active profile:

```bash
hermes config env-path
```

For a named profile, select that profile in the command:

```bash
hermes -p PROFILE_NAME config env-path
```

Typical locations are:

- Default profile: `~/.hermes/.env`
- Named profile: `~/.hermes/profiles/PROFILE_NAME/.env`
- Custom installation: `$HERMES_HOME/.env`

The recommended way to populate the file is to run the plugin installer for the same profile. Hermes asks for the Client ID and Client Secret, hides the Client Secret input, and writes both values to that profile's `.env` file:

```bash
hermes -p PROFILE_NAME plugins install pablousx/hermes-plugin-infisical --enable
```

Omit `-p PROFILE_NAME` only when configuring the default profile. Run this in your own private terminal and enter the values interactively; never paste the Client Secret into an agent conversation.

## Install with a prompt

Paste the prompt below into a Hermes agent. You do not need to paste the Client ID or Client Secret into the prompt. If the Infisical identity has not been prepared yet, the agent must walk you through the browser steps below and then pause while you enter the credentials directly into Hermes' local, interactive installer.

```text
Install and configure the read-only Infisical SecretSource plugin for this Hermes profile.

Plugin repository: pablousx/hermes-plugin-infisical

Instructions:
1. Read the repository README, SECURITY.md, plugin.yaml, and the installed Hermes
   SecretSource/plugin documentation before changing configuration.
2. Ask me only for these non-secret scope values if they are not already known:
   Infisical host/region, project ID, environment slug, secret path, and whether
   child folders should be read recursively. Do not ask me to send the Client
   Secret—or any other secret—in chat.
3. If I have not created the Infisical credentials, guide me through these steps:
   a. In Infisical, open Organization Settings > Access Control > Identities and
      choose Create identity. Give it a descriptive Hermes name and the least
      privileged organization role available.
   b. Keep or configure Universal Auth for the identity. Explain that this is the
      authentication method that provides a Client ID and Client Secret.
   c. On the identity page, choose Create Client Secret. Use a descriptive label
      and a TTL/use limit compatible with repeated Hermes starts and refreshes.
      Tell me to copy the displayed Client ID and new Client Secret to a password
      manager; never ask me to paste either credential into this conversation.
   d. In the target project, open Project Settings > Access Control > Machine
      Identities, choose Add identity, select the new identity, and grant a project
      role that can read secrets but cannot create, edit, or delete them.
   e. In Project Settings, use Copy Project ID. Confirm the environment slug and
      folder path containing the environment-shaped secrets Hermes should load.
4. When the identity is ready, tell me to run this command myself in a private local
   terminal, targeting the same profile as the affected gateway:
   hermes -p PROFILE_NAME plugins install pablousx/hermes-plugin-infisical --enable
   Tell me to omit `-p PROFILE_NAME` only for the default profile. First run
   `hermes -p PROFILE_NAME config env-path` so I can see the exact destination.
   Explain the three prompts before I run it: INFISICAL_HOST_URL is
   https://app.infisical.com for Infisical Cloud US,
   https://eu.infisical.com for Cloud EU, or my self-hosted URL; the Client ID is
   copied from the identity; and the Client Secret is the newly generated value.
   State explicitly that both the Client ID and Client Secret are saved in the
   active profile's .env file: ~/.hermes/.env for the default profile or
   ~/.hermes/profiles/PROFILE_NAME/.env for a named profile. They never belong in
   config.yaml. The installer hides secret input. Pause until I confirm installation
   completed. Never type credentials into a tool call, command argument, log, or
   chat message.
5. After I confirm, verify only that the three required variable names are present;
   never read or print their values. Configure secrets.sources and
   secrets.infisical for the selected scope. Preserve
   INFISICAL_HOST_URL, INFISICAL_UNIVERSAL_AUTH_CLIENT_ID, and
   INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET.
6. Use only those three bootstrap variables for Universal Auth. If any are still
   missing, identify the missing variable by name and return me to the local
   installer step. Never print, log, echo, commit, or include values in tool output.
7. Keep HTTPS required. Do not enable allow_insecure_http unless I explicitly say
   this is a trusted private network.
8. Restart the gateway and verify with `hermes secrets status`. Report only source
   status, provenance, counts, and variable names when necessary. Never dump values
   or the complete process environment.
9. Run a safe smoke test proving that at least one expected credential is attributed
   to Infisical. Do not persist downloaded values to .env or config.yaml.
10. From now on, when a task needs a credential supplied by this source, use the
   environment variable normally. Do not fetch or display the raw value. If it is
   missing, report the variable name and Infisical source status instead of asking
   me to paste the secret into chat.
11. Treat this plugin as read-only. Do not create, update, delete, or rotate Infisical
   secrets through it.
12. Account for Hermes' first-process plugin timing limitation documented in the
    README. Keep credentials required by the initial gateway process in the approved
    bootstrap source until Hermes resolves that limitation.

Finish by reporting the installed plugin version, configuration scope, test result,
and any first-process credentials that could not be migrated. Do not report values.
```

## Debug with a prompt

If installation completed but Infisical secrets are unavailable, paste this prompt into the affected Hermes profile. It tells Hermes to diagnose the failure without displaying credentials or downloaded secret values.

```text
Diagnose and, when safe, repair the Infisical SecretSource plugin for this Hermes
profile.

Plugin repository: pablousx/hermes-plugin-infisical

Rules:
1. Read the installed plugin's README.md, SECURITY.md, plugin.yaml, and the Hermes
   plugin and SecretSource documentation that matches this installation before
   making changes.
2. Never print, return, log, compare, or place in a command argument the values of
   INFISICAL_UNIVERSAL_AUTH_CLIENT_ID,
   INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET, access tokens, or downloaded secrets.
   Do not display ~/.hermes/.env, the process environment, HTTP bodies, or gateway
   log lines that may contain values. Report only variable names and whether each is
   present and non-empty.
3. Confirm which Hermes profile and HERMES_HOME the affected gateway actually uses.
   Diagnose that profile rather than assuming the default ~/.hermes profile.
4. Work through these checks in order and keep sanitized evidence for the report:
   a. Run `hermes plugins list` and confirm that infisical is installed, enabled,
      loaded without a registration error, and sourced from the expected directory.
      If discovery is unclear, run
      `HERMES_PLUGINS_DEBUG=1 hermes plugins list`, but redact any sensitive output.
   b. Confirm that plugin.yaml parses and that the installed files include
      __init__.py and infisical_source.py. Check whether the installed checkout is
      stale or detached at an unintended revision; do not update it until that is
      shown to be the cause.
   c. Check only the presence and non-empty status of INFISICAL_HOST_URL,
      INFISICAL_UNIVERSAL_AUTH_CLIENT_ID, and
      INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET in the affected profile's bootstrap
      environment. Confirm the .env file is outside the plugin repository and has
      restrictive permissions. Never read or reveal the values.
   d. Parse config.yaml and verify: plugins.enabled contains infisical;
      secrets.sources contains infisical; secrets.infisical.enabled is true;
      project_id is non-empty; environment and secret_path are non-empty; recursive
      is boolean; and the three bootstrap variable names are in
      secrets.preserve_existing. Report the configured project ID, environment, and
      path only after asking whether those non-secret identifiers may be shown.
   e. Run `hermes secrets status`. Use its sanitized source status, error kind,
      provenance, counts, warnings, and variable names to classify the failure.
      Never dump secret values or the complete environment.
   f. If networking is implicated, verify DNS, TCP/TLS reachability, certificate
      validation, redirects, and that INFISICAL_HOST_URL is a base URL for the
      correct Cloud region or self-hosted instance. Do not send credentials in a
      manual curl request. Keep HTTPS enabled; do not set allow_insecure_http unless
      I explicitly confirm a trusted private network and accept the risk.
   g. Distinguish authentication failures from authorization or scope failures. An
      authentication failure can mean an expired, revoked, exhausted, IP-restricted,
      mismatched Client ID/Secret, or Universal Auth lockout. A reference/scope
      failure can mean the identity was not added to the project, lacks read access,
      or the project ID, environment slug, folder path, recursion setting, or E2EE
      compatibility is wrong.
   h. Check whether Hermes precedence explains a missing or unexpected value:
      preserve_existing wins; existing values may win when override_existing is
      false; mapped sources outrank bulk sources; and earlier equal-shape sources
      win. Do not reveal either competing value.
   i. Account for the documented first-process plugin timing limitation. Determine
      whether the unavailable credential is required by the initial gateway process
      or only by later children, sessions, or refreshes.
5. You may repair clear local configuration mistakes, enable the installed plugin,
   correct non-secret scope settings that I confirm, restrict .env permissions, and
   restart the gateway. Preserve unrelated configuration and show a value-free diff
   before writing. Ask before reinstalling, updating, changing a network security
   setting, or modifying any credential.
6. If credentials are missing or invalid, do not ask me to paste them into chat.
   Tell me to run `hermes -p PROFILE_NAME config env-path` to identify the affected
   profile's exact .env file, then run the plugin installer for that same profile in
   a private local terminal. State that the installer writes both the Client ID and
   Client Secret to that .env file, never to config.yaml, and have me enter them in
   its interactive prompts. If rotation is required, guide me to the Machine
   Identity's Universal Auth page in Infisical to create a replacement Client
   Secret, enter it locally in the Hermes profile, restart the gateway, verify the
   replacement, and then revoke the old secret. Never perform or claim rotation
   through this read-only plugin.
7. If project access is the cause, tell me exactly where to fix it in Infisical:
   Project Settings > Access Control > Machine Identities. Specify the missing
   read-only role, environment, or path access without requesting secret values.
8. After each safe repair, restart only the affected gateway when necessary and run
   `hermes secrets status` again. Stop retrying after repeated authentication
   failures to avoid triggering or extending Universal Auth lockout.

Finish with: the root cause (or the remaining hypotheses ranked by evidence), checks
performed, sanitized evidence, changes made, verification result, and exact manual
steps still required. Do not report any credential or secret value.
```

## Prepare Infisical

The plugin uses [Universal Auth](https://infisical.com/docs/documentation/platform/identities/universal-auth), so Hermes needs a Machine Identity with read access to the project. These steps use an organization-level identity, which works for both Infisical Cloud and self-hosted Infisical:

1. Open **Organization Settings > Access Control > Identities** in Infisical and select **Create identity**.
2. Give it a recognizable name, such as `hermes-production`, and assign the least-privileged organization role that fits your deployment. Universal Auth is enabled by default; keep it enabled or add it from the identity's **Authentication** section.
3. On the identity page, select **Create Client Secret**. Give the credential a useful description. Choose a TTL and maximum-use count that permit every Hermes restart and secret refresh you expect; `0` means no expiry or use limit in Infisical. Restrict trusted IPs when your Infisical plan and network architecture support it.
4. Copy the identity's **Client ID** and the newly displayed **Client Secret** into a password manager. Treat the Client ID like a username and the Client Secret like a password. If the secret is lost, create a replacement rather than sharing it through chat, tickets, or logs.
5. Open the project that contains the secrets, then go to **Project Settings > Access Control > Machine Identities > Add identity**. Select the identity and grant it a project role that can read secrets but cannot create, edit, or delete them. For least privilege, limit the role to the environment and secret path Hermes needs when your Infisical configuration supports those restrictions.
6. In **Project Settings**, select **Copy Project ID**. Also note the environment slug (for example `prod`) and folder path (for example `/hermes`). Secret keys in that folder should be valid environment variable names, such as `OPENAI_API_KEY`.

An organization role and a project role serve different purposes: adding the identity to the project is required even though the identity already has an organization role. See Infisical's [Machine Identities guide](https://infisical.com/docs/documentation/platform/identities/machine-identities) for the underlying access model.

## Install and store the bootstrap credentials in Hermes

```bash
hermes -p PROFILE_NAME config env-path
hermes -p PROFILE_NAME plugins install pablousx/hermes-plugin-infisical --enable
```

Replace `PROFILE_NAME` with the profile used by the gateway. For the default profile, omit `-p PROFILE_NAME` from both commands. The first command prints the exact `.env` file that will receive the credentials.

When a required value is not already configured, Hermes prompts for it. Enter the values directly in that local installer—not in an agent chat or command-line argument. Hermes writes all three values to the `.env` path printed above:

| Hermes prompt | Value to enter |
|---|---|
| `INFISICAL_HOST_URL` | `https://app.infisical.com` for Infisical Cloud US, `https://eu.infisical.com` for Cloud EU, or the base URL of your self-hosted instance |
| `INFISICAL_UNIVERSAL_AUTH_CLIENT_ID` | The Client ID shown on the Machine Identity page |
| `INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET` | The Client Secret produced by **Create Client Secret**; Hermes hides this input |

The resulting profile `.env` contains these assignments:

```env
INFISICAL_HOST_URL=...
INFISICAL_UNIVERSAL_AUTH_CLIENT_ID=...
INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET=...
```

The Client ID and Client Secret both belong in this `.env` file because they are the bootstrap credentials Hermes needs before the plugin can contact Infisical. They do not belong in `config.yaml`. That file contains only non-secret scope settings such as `project_id`, `environment`, and `secret_path`.

If the plugin was already installed before these values existed, run `hermes -p PROFILE_NAME config env-path` and add the same three entries to the file it prints using a trusted local editor. Do not place the Client Secret directly in a shell command, where it may be retained in shell history. Then restrict that file to mode `600` and restart the same profile's gateway. For the default profile:

```bash
chmod 600 ~/.hermes/.env
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

## Bootstrap environment reference

The resulting Hermes profile contains these three values before it can reach Infisical:

```env
INFISICAL_HOST_URL=https://infisical.example.com
INFISICAL_UNIVERSAL_AUTH_CLIENT_ID=...
INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET=...
```

Keep this bootstrap identity local, out of Git, and protect the containing file with mode `600`. Prefer a separate read-only Machine Identity for each distinct application and permission boundary so credentials can be revoked independently.

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
