# Contributing

To make contributions to this charm, you'll need a working [development setup](https://documentation.ubuntu.com/juju/3.6/howto/manage-your-juju-deployment/set-up-your-juju-deployment-local-testing-and-development/).

You can create an environment for development with `tox`:

```shell
tox devenv -e integration
source venv/bin/activate
```

## Testing

This project uses `tox` for managing test environments. There are some pre-configured environments
that can be used for linting and formatting code when you're preparing contributions to the charm:

```shell
tox run -e format        # update your code according to linting rules
tox run -e lint          # code style
tox run -e unit          # unit tests
tox run -e integration   # integration tests
tox                      # runs 'format', 'lint', and 'unit' environments
```

## Build the charm

Build the charm in this git repository using:

```shell
charmcraft pack
```

## Release the charm

Our release note policy is described in our [documentation](https://documentation.ubuntu.com/haproxy-charm/latest/release-notes/).

It is implemented by this [workflow](https://github.com/canonical/haproxy-operator/deployments/charmhub-stable-promote) that is triggered automatically on Monday.

To give the required approval, click on the three horizontal dots on the right of the screen.

Once the charm has been published to `stable`:

- Create a PR to list the content for the [release note](https://github.com/canonical/haproxy-operator/tree/main/docs/release-notes/releases).

  - Include all PR merged into the release published to stable and not listed in the previous release.

- Once merged, a new [Add release notes](https://github.com/canonical/haproxy-operator/pulls) PR will be automatically created.

  - Edit it to refine the release notes.

- Once merged, announce the new release on [Charmhub](https://discourse.charmhub.io/c/announcements-and-community/33) (tags: "charms" and "haproxy").
