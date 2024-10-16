<!-- markdownlint-disable -->

<a href="../src/legacy.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `legacy.py`
Legacy haproxy module. 

IMPORTANT: This module contains the code of the legacy haproxy charm with some modifications to work with the ops framework. It does not match the quality standard for actively managed charms. However, we are using it here to ensure that the new  haproxy charm can serve as a drop-in replacement for the legacy haproxy charm and  that the behavior is the same between the 2. 

**Global Variables**
---------------
- **default_haproxy_lib_dir**
- **dupe_options**
- **frontend_only_options**
- **default_haproxy_service_config_dir**
- **DEFAULT_SERVICE_DEFINITION**

---

<a href="../src/legacy.py#L88"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `parse_services_yaml`

```python
parse_services_yaml(services, yaml_data)
```

Parse given yaml services data.  Add it into the "services" dict.  Ensure that you union multiple services "server" entries, as these are the haproxy backends that are contacted. 


---

<a href="../src/legacy.py#L125"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `is_proxy`

```python
is_proxy(service_name)
```






---

<a href="../src/legacy.py#L130"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `comma_split`

```python
comma_split(value)
```






---

<a href="../src/legacy.py#L134"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `merge_service`

```python
merge_service(old_service, new_service)
```

Helper function to merge two service entries correctly. Everything will get trampled (preferring old_service), except "servers" which will be unioned across both entries, stripping strict dups. 


---

<a href="../src/legacy.py#L170"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `ensure_service_host_port`

```python
ensure_service_host_port(services)
```






---

<a href="../src/legacy.py#L204"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `get_services_from_relation_data`

```python
get_services_from_relation_data(relation_data)
```






---

<a href="../src/legacy.py#L330"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `create_listen_stanza`

```python
create_listen_stanza(
    service_name=None,
    service_ip=None,
    service_port=None,
    service_options=None,
    server_entries=None,
    service_errorfiles=None,
    service_crts=None,
    service_backends=None
)
```






---

<a href="../src/legacy.py#L408"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `generate_service_config`

```python
generate_service_config(services_dict)
```






---

<a href="../src/legacy.py#L451"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `get_service_lib_path`

```python
get_service_lib_path(service_name)
```






---

<a href="../src/legacy.py#L460"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `write_ssl_pem`

```python
write_ssl_pem(path, content)
```

Write an SSL pem file and set permissions on it. 


---

## <kbd>class</kbd> `InvalidRelationDataError`
Invalid data has been provided in the relation. 





