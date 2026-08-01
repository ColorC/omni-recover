# Security policy

## Sensitive inputs

AI session data is sensitive even when the tool itself is public. A transcript
or index may contain proprietary source, prompts, local usernames and paths,
terminal output, environment values or credentials. Keep evidence archives
outside the repository on access-controlled encrypted storage. Do not attach
real session data to a public issue.

## Reporting a vulnerability

Open a GitHub security advisory for vulnerabilities in parsing, path
containment, overwrite protection, snapshot/journal handling or credential
exposure. For a public bug report, use synthetic fixtures only.

## Recovery boundary

The alpha release writes only after an explicit `--apply`, a confirmed
workspace root and a pre-apply snapshot. It does not replay recorded commands.
Project semantics remain outside the generic byte-recovery guarantee.
