(changelog)=

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

Each revision is versioned by the date of the revision.

## 2026-01-14

- Added provider support for the `ddos_protection` interface on the HAProxy charm.

## 2026-01-09

- Updated HAProxy config to track connections per minute instead of rate limit.

## 2026-01-08

- Added the provider side of the `ddos-protection` interface.

## 2025-12-17

- Added the DDoS defaults in the HAProxy config files and a config option to disable the defaults.

## 2025-12-19

- Added `app_name` and missing endpoint outputs to the Terraform product.

## 2025-12-19

- Added support for custom gRPC frontend port using the `external_grpc_port` attribute.

## 2025-12-18

- Added the `ddos_protection` interface.
- Parametrize app_name for subordinates in Terraform product.

## 2025-12-11

- Added the skeleton code for the HAProxy DDoS protection configurator charm.

## 2025-11-27

- Updated the change artifact compliance workflow with an opt-out ability.

## 2025-11-24

- Added HTTP/2 support to HAProxy for both frontend and backend configurations.

## 2025-11-14

- Added GitHub workflow that checks whether a pull request contains a change artifact.

## 2025-11-13

- Added the `spoe-auth` library and requirer/provider class implementation.

## 2025-11-12

- Updated the haproxy-route library to add the `allow_http` attribute.

## 2025-10-14

- Added action `get-proxied-endpoints`.

## 2025-10-08

- Upgrading HAproxy apt package to `2.8.5-1ubuntu3.4`.

## 2025-09-23

- Add documentation for security practices.

## 2025-08-20

- Release notes for 2.8/stable were added.

## 2025-08-11

- Changelog added for tracking changes.
