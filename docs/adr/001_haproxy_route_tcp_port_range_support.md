---
title: ADR-001 - Port range support for the haproxy-route-tcp relation
author: Thanhphan1147
date: 2026/06/24
domain: architecture
replaced-by:
---

# Port range support for the `haproxy-route-tcp` relation

The `haproxy-route-tcp` relation library (v1, LIBPATCH 5) gains a `port_mapping` attribute on `TcpRequirerApplicationData` so that workloads listening on a port range can be exposed through HAProxy without requiring one relation per port.

## Decision

### Format: plain string in the relation databag

The `port_mapping` field is stored as a plain string (`"<frontend_range>"` or `"<frontend_range>:<backend_range>"`, e.g. `"4000-4005"` or `"4000-4005:5000-5005"`) in the `TcpRequirerApplicationData` relation databag. 

#### Alternatives

Storing the field as a dedicated dataclass.

#### Rationale

We decided not to explicitly model the mapping using a dataclass because the syntax is very well known and parsing/validation is relatively simple. `port_mapping` is mutually exclusive with the existing `port` / `backend_port`
fields, enforced by a model-level validator.

### Conflict detection and merging

For "port-range" requirers, any overlapping ranges will be considered invalid, and "port-range" requirers must request for completely isolated port ranges.

Merging is done by applying the following rules:

* R1: "port-range" requirers can't be merged together
* R2: One or more "single-port" requirers can be merged with a "port-range" requirer if:
  * They share the same TLS termination configuration as the "port-range" requirer (passthrough or terminate)
  * They have set an SNI for SNI-routing
  * The requested port fall into the port range requested by the "port-range" requirer

#### Alternatives

Merge "port-range" requirers requesting for exactly the same range together, using the same logic as with "single-port" requirers.

#### Rationale

To keep it simple and to make our intention clear that the `port-mapping` feature is intended to be used for specific protocol that requires it, rather than a shortcut to compress the number of relations on a requirer, we won't be providing merging support for "port-range" requirers for now.

We support merging "single-port" requirers with "port-range" requirers to be consistent since "single-port" requirers were already being merged.
