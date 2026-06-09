---
name: pr-best-practices
description: >
  Analyzes a merged LLM-authored PR by comparing its first commit (the LLM's initial output)
  with the final merged state (after human reviews and code changes), then synthesizes do's
  and don'ts into .github/instructions/best-practices.instructions.md so Copilot automatically
  uses these lessons in future sessions. Use this skill whenever the user wants to learn from a PR's
  review cycle, extract project philosophy or coding style from AI-generated code revisions, update
  best practices based on reviewer feedback, or says anything like "analyze PR #N", "extract lessons
  from this PR", "update best practices", or "what did reviewers change in this PR".
---

# PR Best Practices Extractor

Extracts coding lessons from the gap between what an LLM initially generated in a PR and what
reviewers changed before merging. The result is a growing `.github/instructions/best-practices.instructions.md`
file that Copilot automatically picks up in every future session.

When the review comments reveal a broader design rule, phrase it as a reusable project principle
rather than only describing the local fix. For example, if reviewers move branching or computed
values out of a Jinja2 template, turn that into a rule about keeping templates declarative and
computing rendered values in charm-state dataclasses or helper builders first.

Use a plain reminder when the advice is already obvious on its face, like library version bumps or
adding unit tests. Reserve Do/Don't pairs for cases where the contrast itself teaches something;
when you do use them, keep both sides centered on the same idea and put extra explanation in the
section intro instead of padding the bullets.

Bundle reusable deterministic helpers as scripts under the skill directory. Call them from the
skill instructions when they remove repeated parsing, fetching, or validation work from the model.
Keep scripts small, single-purpose, and easy to reuse across iterations; leave one-off reasoning in
the skill body instead of turning every step into code.

## Input

The user provides a PR number (e.g. `#123` or just `123`), and optionally a repository
in `owner/repo` format. If no repository is given, use the current repository.

## Workflow

### Step 1: Fetch PR metadata

Retrieve the PR's title, URL, base branch, merged status, and the list of all commits
(in order). The PR must be merged — if it isn't, report that and stop.

### Step 2: Identify first and final iterations

- **First iteration**: the very first commit in the PR — this is what the LLM produced.
- **Final iteration**: the merged commit (or the last commit before merge).

Use the GitHub API or `git` to get the full unified diff between the tree at the first
commit and the tree at the final commit. Focus on source files and not generated or lock files.
Also read review comments on the PR, because they often reveal the broader architectural pattern
behind a change even when the final diff only shows the end result.

For **test files only** (`**/tests/**/*.py`), also compute:
- Diff A: `base_branch_sha -> first_commit_sha`
- Diff B: `first_commit_sha -> final_commit_sha`

Only derive test-specific rules from Diff B hunks that correspond to test files that already
had meaningful changes in Diff A. If a test file appears only in Diff B (i.e., no meaningful
test diff in Diff A), treat that simply as "tests were added later".

The most important source files present in this repo are:
- `**/*.py`: Charm code and test code
- `haproxy-operator/*.j2`: Jinja2 templates used to render the HAProxy configuration
- `**/*.yaml`: Charmcraft or snapcraft files used to pack the corresponding snap/charm

### Step 3: Assess significance

A diff is **significant** if it contains any of the following:
- Logic or behaviour changes (not just whitespace / formatting)
- Added, removed, or restructured tests
- Changes to public interfaces, APIs, or configuration schemas
- Improved error handling, edge case coverage, or robustness
- Refactoring that improves clarity, naming, or structure

If the diff is **not significant** (only cosmetic changes), report this clearly and stop.
There is nothing actionable to extract.

### Step 4: Analyse the changes

For each significant change, determine:
- **What the LLM did first** — the initial pattern or approach
- **What it became** — the corrected or improved version after review
- **Why it changed** — the underlying principle or best practice being applied

Use review comments alongside the diff when the comments explain a deeper architectural preference
or layering boundary that is not obvious from code changes alone.
The review-comment helper is the source of truth for pulling that discussion into the analysis.

Group changes by theme. Common themes for this codebase include:
- Testing patterns (unit vs integration, fixtures, mocking)
- Error handling and defensive coding
- Juju charm lifecycle and relation handling
- Code structure and module organisation
- Naming and readability
- Security and input validation
- Documentation and type hints
- Project philosophy and layering boundaries
- Rendering boundaries between state objects and Jinja2 templates

### Step 5: Synthesize rules with code examples

For each theme, produce clear, actionable rules in two categories:

**Do** — positive patterns to follow (what reviewers moved the code *toward*)  
**Don't** — anti-patterns to avoid (what reviewers moved the code *away from*)

Rules must be:
- Specific enough to be actionable (not "write good code")
- Grounded in the actual diff — if you can't point to the evidence, don't include the rule
- Generalizable beyond this specific PR
- High-level enough to be useful across multiple PRs — avoid rules that are essentially a description of one implementation detail (e.g. "use `is_allow_http` as the ACL name"). Ask yourself: would a developer writing a different feature in this codebase benefit from this rule? If the rule only makes sense in the exact context of the diff, it is too narrow.

When the diff suggests an architectural preference, spell it out. For example: "Keep Jinja2
templates declarative; compute derived values in charm-state dataclasses or helper builders before
rendering." The example should show the logic moving into state and the template becoming a pure
renderer.

Keep each Do/Don't pair focused on the same underlying idea. Put any extra explanation in the
theme or subsection intro, then keep the Do and Don't bullets themselves mostly to the concrete
example so the output stays easy to scan.

**Every rule must include a code example drawn directly from the diff.** Show the before
(what the LLM wrote) and after (what the reviewer changed it to). Use the actual variable
names, function signatures, and patterns from the PR — not invented pseudocode. If the
change is too large to quote fully, extract the most illustrative 5–15 lines.

Special case for tests added only after the first commit:
- If test files have no meaningful Diff A changes but do have Diff B additions, collapse this
  into a single generic testing reminder rule for that PR:
  - **Don't**: "Don't forget to add tests."
- In this case, include one concrete "after" snippet from the added tests as evidence, and
  explicitly note that there was no corresponding first-commit test implementation to compare.

### Step 6: Propose changes to `.github/instructions/best-practices.instructions.md`

After synthesizing all rules, do **not** write directly to the file. Instead, present each
proposed change to the user one at a time for review before applying anything.

For each proposed change, show:
- **What**: the rule or section being added or modified
- **Why**: the evidence from the diff or review comments that justifies it
- **Format**: the exact text as it would appear in the file

Then wait for the user to confirm ("yes", "accept", "looks good") or reject/modify before moving to
the next proposal. Only apply the change to the file once the user has confirmed it.

Once all proposals have been reviewed and confirmed, apply all accepted changes in a single edit.

The accepted formats are:

1. **Plain reminder** for obvious guidance:

```markdown
## [Theme Name]

[Short reminder sentence.]
```

2. **Lean Do/Don't pair** when the contrast teaches something:

```markdown
## [Theme Name]

[Short context sentence explaining the underlying idea.]

### Do
- [Concise positive rule] ([PR #N](url))

  ```python
  [concrete code from the diff]
  ```

### Don't
- [Concise anti-pattern] ([PR #N](url))

  ```python
  [concrete code from the diff]
  ```
```

Keep Do/Don't bullets focused on the same idea. Put extra explanation in the section intro, and
use a Do/Don't pair only when it adds value over a plain reminder.

**If the file does not exist**, propose creating it with this skeleton as the first proposal:

```markdown
---
description: 'Accumulated best practices extracted from LLM-authored PR reviews'
applyTo: '**'
---

# Best Practices

Lessons learned from reviewing LLM-authored pull requests in this repository.
Each rule is linked to the PR where the pattern was first observed.

<!-- Add new themes and rules below this line -->
```

### Step 7: Report

Summarise what was done:
- Whether `best-practices.instructions.md` was created or updated
- How many new rules were added
- Which themes were covered
- A short preview of the most impactful rule added

## Notes

- The first commit is the LLM's raw output; everything that changed after that reflects
  human judgment. That delta is the signal.
- If a PR has dozens of commits, still only compare the *first* commit tree vs the *merged*
  tree — intermediate steps are noise.
- Exception for tests: use both `base -> first` and `first -> final` to decide whether a
  test change reflects reviewer refinement or simply late addition of missing tests.
- When the same anti-pattern appears across multiple PRs, consolidate into one rule and
  list all PR references.
- Prefer specificity over generality. "Always call `relation.data[self.app].update()`
  inside `_on_relation_joined`" is more useful than "use relations correctly".
