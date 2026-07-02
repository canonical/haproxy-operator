---
title: ADR-001 - Port range support for the haproxy-route-tcp relation
author: Thanhphan1147
date: 2026/06/24
domain: architecture
replaced-by:
---

# Port range support for the `haproxy-route-tcp` relation

The `haproxy-route-tcp` relation library (v1, LIBPATCH 5) gains a `port_mapping` attribute on `TcpRequirerApplicationData` so that workloads listening on a port range can be exposed through HAProxy without requiring one relation per port.

## Context

Workloads such as database shards and protocols like FTP operate on a port range (e.g. 4000–4005). Before this change, each port required a separate `haproxy-route-tcp` relation and produced a separate HAProxy frontend bound to a single port. For a range of N ports this produces N frontends, N bind sockets, and a correspondingly large HAProxy config that grows proportionally with the range size.

HAProxy natively supports binding a frontend to a port range with a single `bind [::]:4000-4005` directive, routing each connection to the appropriate backend port via a constant arithmetic offset applied to the incoming destination port. The existing library and operator did not expose this capability.

Additionally, there is a use case for separate frontend and backend port ranges — for example, a workload internally uses ports 5000–5005 but must be exposed on 4000–4005. A port mapping string of the form `"4000-4005:5000-5005"` captures both ranges concisely.

## Decision

### Format: plain string in the relation databag

The `port_mapping` field is stored as a plain string (`"<frontend_range>"` or `"<frontend_range>:<backend_range>"`, e.g. `"4000-4005"` or `"4000-4005:5000-5005"`) in the `TcpRequirerApplicationData` relation databag. We decided not to explicitly model the mapping using a dataclass because the syntax is very well known and parsing/validation is relatively simple. `port_mapping` is mutually exclusive with the existing `port` / `backend_port`
fields, enforced by a model-level validator.

### Port translation via `set-dst-port` arithmetic

When the frontend and backend ranges differ, the backend port is derived from the frontend port using a constant arithmetic offset:

```
tcp-request content set-dst-port dst_port,add(<offset>)
```

The `offset` is `backend.start - frontend.start`. When both ranges are identical the offset is zero and no translation directive is emitted.

Server entries in the backend config omit the explicit port (i.e. `server name <address>` with no `:port`) when the backend is a port range, and the config relies on `set-dst-port` to determine the backend port.


### Conflict detection

We classify requirers for the `haproxy-route-tcp` relation into 2 types: "single-port" requirers that either sets the `port` and `backend_port` attribute or sets single value for the `port-mapping` attribute ( e.g `4000-4000:5000-5000`) ( from now on will be referenced as `type 1` ) and "port-range" requirers that sets the `port-mapping` attribute to port ranges of len > 1 ( `type 2` ).

There's no change for type 1 requirers with regards to conflict detection

For type 2 requirers, any overlapping ranges will be considered invalid, and type 2 requirers must request for completely isolated port ranges.

## Merging

Merging is done by applying the following rules:

* R1: Type 2 requirers can't be merged together
* R2: One or more type 1 requirers can be merged with a single type 2 requirer if:
  * They share the same TLS termination configuration as the type 2 requirer (passthrough or terminate)
  * They have set an SNI for SNI-routing
  * The requested port fall into the port range requested by the type 2 requirer

To keep it simple and to make our intention clear that the `port-mapping` feature is intended to be used for specific protocol that requires it, rather than a shortcut to compress the number of relations on a requirer, we won't be providing merging support for type 2 requirers for now.