# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "app_name" {
  description = "Name of the deployed haproxy application."
  value       = module.haproxy.haproxy-application-name
}
