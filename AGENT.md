# AGENT.md

## Database Changes
- Every schema change MUST be done through a migration file. Never run raw ALTER/DROP/CREATE statements directly against the database or hand-edit the schema.
- Migrations MUST be reversible. Write both `up` and `down` steps. If a migration is genuinely irreversible (e.g. dropping a column with data loss), do NOT run it — treat it as a hard decision (see below) and get explicit user sign-off first.
- Never combine destructive and additive changes in one migration. Deprecate/backfill first, drop later.
- Each migration file gets a one-line comment stating *why*, not just *what*.

## Testing
- Every new feature ships with at least one test covering its main behavior plus one edge case, before the task is marked done.
- Every bug fix ships with a regression test that fails on the old code and passes on the fix.
- Run the full test suite before reporting a task complete. If a test fails, fix it or report it — never skip or comment it out to get a task "done."

## Decision-Making
Do NOT unilaterally resolve decisions in these categories — stop and ask the user, with 2-3 options and a recommendation:
- Irreversible or destructive actions (data deletion, force-push, dropping tables)
- Architecture/design choices that touch multiple modules or are expensive to reverse later
- Security, auth, or permissions tradeoffs
- Anything where you're choosing between two reasonable approaches and picking wrong would mean redoing real work

You CAN decide autonomously: naming, internal refactors, adding helper functions, formatting, anything cheaply reversible within the same task.

## Change Logging
- Every task that changes code, config, or schema MUST add an entry to `CHANGES.md` before being marked complete.
- Entry format, newest entry on top:

  > \## [YYYY-MM-DD] Short title
  >
  > - What changed: 1-2 lines
  > - Why: the triggering feature/bug/decision
  > - Files: key files touched
  > - Migration: yes/no (link if yes)

- Bug fixes must name the root cause, not just "fixed X" — e.g. "Fixed race condition in key rotation caused by missing lock on `refresh_token()`."
- Don't batch multiple unrelated changes into one entry. One task = one entry (or one entry per logical change if a task touches several things).
- `CHANGES.md` is append-only during normal work — don't rewrite or delete past entries except to correct a factual error in the log itself.

## Tests
Ensure that you focus on these checks:
- Authentication/authorization
- Role permissions
- Tenant isolation
- Tenant expiration
- Course assignment
- Learning progress

You do not need 100% test coverage. Focus on meaningful cases and important edge cases.

## Notes
- Focus on producing minimal code, as it is a Demo Project.
- Write tests can be resued in future, so that you don't need to generate new tests by buring additional tokens.
- Ensuer that the Qualitiy of Backend meets production grade.