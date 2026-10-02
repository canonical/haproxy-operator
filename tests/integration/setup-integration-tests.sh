#!/bin/bash
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

set -exo pipefail

sudo k8s config | juju add-k8s ck8s --client
