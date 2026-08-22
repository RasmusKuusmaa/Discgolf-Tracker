# Contribution rules for this repository

1. **Work top to bottom** through the active task list. Do not skip ahead. Do not
   batch multiple checkboxes into one commit.
2. **Commit after every single checkbox.** Use the exact commit message specified
   for that checkbox.
3. **Commit messages must NOT be signed.** No `Co-Authored-By:` line, no
   "Generated with Claude Code", no emoji footer, no trailers of any kind. The
   commit message is exactly the one line given, nothing else.
4. **If a checkbox needs more than ~150 lines of change**, split it into
   sub-steps and write conventional-commit one-liners for each sub-step. Smaller
   commits are always better.
5. **Never commit broken code.** If a checkbox touches compiled/tested code, the
   build must pass before committing.
6. **Do not invent scope.** Anything not in the active task list goes into
   `BACKLOG.md`, not the codebase.
7. **Do not scrape UDisc, PDGA, or any commercial disc golf database.** Course
   seed data comes from OpenStreetMap (Overpass API, ODbL — attribution
   required) or from users.
8. After each phase, run the full test suite and fix anything red before moving
   on.

Commit style: [Conventional Commits](https://www.conventionalcommits.org/)
(`feat:`, `fix:`, `chore:`, `refactor:`, `test:`, `docs:`, `build:`, `ci:`).
Scope in parentheses where useful, e.g. `feat(backend): add user model`.
