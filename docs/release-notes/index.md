---
myst:
  html_meta:
    "description lang=en": "History of stable releases for the HAProxy charm."
---

(release_notes_index)=

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

For any given track, we'll implement three different risk levels `edge`, `candidate`, and `stable`. The release schedule for each of the risk levels is as follows:

1. Changes pushed to the `haproxy-operator` repository will be released to `edge`.
2. On Monday of every week, the current revision on `candidate` will be promoted to `stable`. This process requires an approval from the maintainers and happens automatically once the approval is given.
3. On Monday of every week, the current revision on `edge` will be promoted to `candidate`. This process also requires an approval from the maintainers and happens automatically once the approval is given.

In special cases where an urgent fix is needed on `stable` changes can be pushed directly to that risk level without going through the regular process.

Release notes are published for the `haproxy` charm with every revision of the `2.8/stable` track.

## Releases

* {ref}`HAProxy release notes – 2.8/stable, revision 216 <release_notes_release_notes_rev216>`
* {ref}`HAProxy release notes – 2.8/stable, revision 283 <release_notes_release_notes_0001>`
* {ref}`HAProxy release notes – 2.8/stable, revision 290 <release_notes_release_notes_0002>`
* {ref}`HAProxy release notes – 2.8/stable, revision 314 <release_notes_release_notes_0003>`
* {ref}`HAProxy release notes – 2.8/stable, revision 339 <release_notes_release_notes_0004>`

```{toctree}
:hidden:
:maxdepth: 1
Revision 216 <release-notes-rev216>
Revision 283 <release-notes-0001>
Revision 290 <release-notes-0002>
Revision 314 <release-notes-0003>
Revision 339 <release-notes-0004>
```
