<!-- markdownlint-disable -->

<a href="../src/haproxy.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `haproxy.py`
The haproxy service module. 

**Global Variables**
---------------
- **APT_PACKAGE_VERSION**
- **APT_PACKAGE_NAME**
- **HAPROXY_USER**
- **HAPROXY_DH_PARAM**
- **HAPROXY_SERVICE**
- **HAPROXY_J2_TEMPLATE_MAPPING**

---

<a href="../src/haproxy.py#L150"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `render_file`

```python
render_file(path: Path, content: str, mode: int) → None
```

Write a content rendered from a template to a file. 



**Args:**
 
 - <b>`path`</b>:  Path object to the file. 
 - <b>`content`</b>:  the data to be written to the file. 
 - <b>`mode`</b>:  access permission mask applied to the  file using chmod (e.g. 0o640). 


---

## <kbd>class</kbd> `HAProxyService`
HAProxy service class. 




---

<a href="../src/haproxy.py#L80"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `install`

```python
install() → None
```

Install the haproxy apt package. 



**Raises:**
 
 - <b>`RuntimeError`</b>:  If the service is not running after installation. 

---

<a href="../src/haproxy.py#L106"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `is_active`

```python
is_active() → bool
```

Indicate if the haproxy service is active. 



**Returns:**
  True if the haproxy is running. 

---

<a href="../src/haproxy.py#L95"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `reconcile`

```python
reconcile(proxy_mode: ProxyMode, config: CharmConfig, **kwargs: Any) → None
```

Render the haproxy config and restart the haproxy service. 



**Args:**
 
 - <b>`proxy_mode`</b>:  proxy mode to decide which template to render. 
 - <b>`config`</b>:  The charm's configuration. 
 - <b>`kwargs`</b>:  Additional args specific to the child templates. 


---

## <kbd>class</kbd> `HaproxyInvalidRelationError`
Exception raised when both the reverseproxy and ingress relation are established. 





---

## <kbd>class</kbd> `HaproxyServiceReloadError`
Error when reloading the haproxy service. 





---

## <kbd>class</kbd> `ProxyMode`
StrEnum of possible http_route types. 

Attrs:  INGRESS: when ingress is related.  LEGACY: when reverseproxy is related.  NOPROXY: when haproxy should return a default page.  INVALID: when the charm state is invalid. 





