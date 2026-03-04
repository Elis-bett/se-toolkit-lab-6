---
name: review-task-conceptual
description: Review a task file for conceptual problems from a practical and educational point of view
argument-hint: "<path>"
---

Review a single task file for conceptual problems — issues with educational value, student experience, task flow, and practical usability. This is distinct from convention review (formatting, naming, structure); conceptual review evaluates whether the task works as a learning experience.

## Steps

1. Parse `$ARGUMENTS` to get the file path. Accept paths under `lab/tasks/` (e.g., `lab/tasks/setup.md`, `lab/tasks/required/task-2.md`). If the path is missing or does not point to a file under `lab/tasks/`, ask the user.
2. Read the target file.
3. Read `instructors/context/conventions/tasks.md` — Section 13 defines the ten review dimensions (D1–D10) and the severity scale to use.
4. Analyse the file against each dimension (D1–D10). For each problem found, record: the dimension, the line number(s) or section, a short description of the problem, and a suggested fix.

## Rules

- Focus on *conceptual and educational* problems only. Do not flag formatting or naming issues — those belong to `/review-via-conventions`.
- Do not invent problems. Ground every finding in the task content and the design principles in `instructors/context/conventions/tasks.md`.
- Be specific: quote the problematic text or give the exact line number. Don't write "step 3 is unclear" — explain what is unclear and why a student would be confused.
- Do not fix anything — only report.

## Output format

Write the report to `tmp/conceptual-problems/<path-relative-to-lab/tasks>`, where `<path-relative-to-lab/tasks>` is the file path with `lab/tasks/` stripped (e.g., for `lab/tasks/required/task-2.md`, write to `tmp/conceptual-problems/required/task-2.md`). Create intermediate directories if they do not exist.

The report must be self-contained. Structure:

1. **Header** — file reviewed, date.
2. **Findings** — grouped by dimension (D1–D10). Under each dimension, list findings as numbered items with:
   - Severity: `[High]`, `[Medium]`, or `[Low]`
   - Line number(s) or section name
   - Description of the problem
   - Suggested fix
   If a dimension has no findings, write "No issues found."
3. **Summary** — total finding count by severity, and a short overall assessment of whether the task is ready for students.

After writing the file, print its path in the conversation so the user can find it.
