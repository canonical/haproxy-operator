# Contributing

This document explains the processes and practices recommended for contributing enhancements to the HAProxy Operator.

## Overview

- Generally, before developing enhancements to this charm, you should consider [opening an issue
  ](https://github.com/canonical/haproxy-operator/issues) explaining your use case.
- If you would like to chat with us about your use-cases or proposed implementation, you can reach
  us at [Canonical Matrix public channel](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)
  or [Discourse](https://discourse.charmhub.io/).
- Familiarizing yourself with the [Juju documentation](https://documentation.ubuntu.com/juju/3.6/howto/manage-charms/)
  will help you a lot when working on new features or bug fixes.
- All enhancements require review before being merged. Code review typically examines
  - code quality
  - test coverage
  - user experience for Juju operators of this charm.
- Once your pull request is approved, we squash and merge your pull request branch onto
  the `main` branch. This creates a linear Git commit history.
- For further information on contributing, please refer to our
  [Contributing Guide](https://github.com/canonical/is-charms-contributing-guide).

## Code of conduct

When contributing, you must abide by the
[Ubuntu Code of Conduct](https://ubuntu.com/community/ethos/code-of-conduct).

## Changelog

Please ensure that any new feature, fix, or significant change is documented by
adding an entry to the [CHANGELOG.md](docs/changelog.md) file. Use the date of the
contribution as the header for new entries.

To learn more about changelog best practices, visit [Keep a Changelog](https://keepachangelog.com/).

## Submissions

If you want to address an issue or a bug in this project,
notify in advance the people involved to avoid confusion;
also, reference the issue or bug number when you submit the changes.

- [Fork](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/about-forks)
  our [GitHub repository](https://github.com/canonical/haproxy-operator)
  and add the changes to your fork, properly structuring your commits,
  providing detailed commit messages and signing your commits.
- Make sure the updated project builds and runs without warnings or errors;
  this includes linting, documentation, code and tests.
- Submit the changes as a
  [pull request (PR)](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request-from-a-fork).

Your changes will be reviewed in due time; if approved, they will be eventually merged.

### AI

You are free to use any tools you want while preparing your contribution, including
AI, provided that you do so lawfully and ethically.

Avoid using AI to complete issues tagged with the "good first issues" label. The
purpose of these issues is to provide newcomers with opportunities to contribute
to our projects and gain coding skills. Using AI to complete these tasks
undermines their purpose.

We have created instructions and tools that you can provide AI while preparing your contribution: [`copilot-collections`](https://github.com/canonical/copilot-collections)

While it isn't necessary to use `copilot-collections` while preparing your
contribution, these files contain details about our quality standards and
practices that will help the AI avoid common pitfalls when interacting with
our projects. By using these tools, you can avoid longer review times and nitpicks.

If you choose to use AI, please disclose this information to us by indicating
AI usage in the PR description (for instance, marking the checklist item about
AI usage). You don't need to go into explicit details about how and where you used AI.

Avoid submitting contributions that you don't fully understand.
You are responsible for the entire contribution, including the AI-assisted portions.
You must be willing to engage in discussion and respond to any questions, comments,
or suggestions we may have. 

### Signing commits

To improve contribution tracking,
we use the [Canonical contributor license agreement](https://assets.ubuntu.com/v1/ff2478d1-Canonical-HA-CLA-ANY-I_v1.2.pdf)
(CLA) as a legal sign-off, and we require all commits to have verified signatures.

#### Canonical contributor agreement

Canonical welcomes contributions to the HAProxy Operator. Please check out our
[contributor agreement](https://ubuntu.com/legal/contributors) if you're interested in contributing to the solution.

The CLA sign-off is simple line at the
end of the commit message certifying that you wrote it
or have the right to commit it as an open-source contribution.

#### Verified signatures on commits

All commits in a pull request must have cryptographic (verified) signatures.
To add signatures on your commits, follow the
[GitHub documentation](https://docs.github.com/en/authentication/managing-commit-signature-verification/signing-commits).

## Develop

To make contributions to this charm, you'll need a working [development setup](https://documentation.ubuntu.com/juju/3.6/howto/manage-your-juju-deployment/set-up-your-juju-deployment-local-testing-and-development/).

You can create an environment for development with `tox`:

```shell
tox devenv -e integration
source venv/bin/activate
```

## Test

This project uses `tox` for managing test environments. There are some pre-configured environments
that can be used for linting and formatting code when you're preparing contributions to the charm:

* ``tox``: Executes all of the basic checks and tests (``lint``, ``unit``, and ``format``).
* ``tox -e format``: Updates your code according to linting rules.
* ``tox -e lint``: Runs a range of static code analysis to check the code.
* ``tox -e unit``: Runs the unit tests.
* ``tox -e integration``: Runs the integration tests.

## Build the charm

Build the charm in this git repository using:

```shell
charmcraft pack
```

## Release the charm

Our release note policy is described in our [documentation](https://documentation.ubuntu.com/haproxy-charm/latest/release-notes/).

It is implemented by this [workflow](https://github.com/canonical/haproxy-operator/deployments/charmhub-stable-promote) that is triggered automatically on Monday.

To give the required approval, click on the three horizontal dots on the right of the screen.

- Once the charm has been published to `stable`:

  - Create a PR to list the content for the [release note](https://github.com/canonical/haproxy-operator/tree/main/docs/release-notes/releases).
  - Include all PR merged into the release published to stable and not listed in the previous release.

- Once merged, a new [Add release notes](https://github.com/canonical/haproxy-operator/pulls) PR will be automatically created.

  - Edit it to refine the release notes.

- Once merged, announce the new release on [Charmhub](https://discourse.charmhub.io/c/announcements-and-community/33) (tags: "charms" and "haproxy").
