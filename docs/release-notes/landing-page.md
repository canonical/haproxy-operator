# Release notes

Release notes for the `2.8/stable` track of HAProxy, summarizing new features,
bug fixes and backwards-incompatible changes in each revision.

<!--
TODO: add upgrade documentation
For upgrading the charm, see [How to upgrade](link to upgrade documentation).
For instructions on a specific release, see the corresponding release notes.
-->

## Release policy and schedule

This section covers the release policy and schedule for the `haproxy` charm and the `haproxy-spoe-auth` charm.

For any given track, we'll implement three different risk levels `edge`, `candidate`, and `stable`. The release schedule for each of the risk level is as follow:
1. Changes pushed to the `haproxy-operator` repository will be release to `edge`.
2. On Monday of every week, the current revision on `candidate` will be promoted to `stable`. This process requires an approval from the maintainers and happens automatically once the approval is given.
3. On Monday of every week, the current revision on `edge` will be promoted to `candidate`. This process also requires an approval from the maintainers and happens automatically once the approval is given.

In special cases where an urgent fix is needed on `stable` changes can be pushed directly to that risk level without going through the regular process.

Release notes are published for the `haproxy` charm with every revision of the `2.8/stable` track.

## Releases

* [HAProxy release notes – 2.8/stable, revision 216](release-notes-rev216.md)