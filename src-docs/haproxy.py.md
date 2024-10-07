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

---

<a href="../src/haproxy.py#L106"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

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

<a href="../src/haproxy.py#L50"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `install`

```python
install() → None
```

Install the haproxy apt package. 



**Raises:**
 
 - <b>`RuntimeError`</b>:  If the service is not running after installation. 

---

<a href="../src/haproxy.py#L74"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `is_active`

```python
is_active() → bool
```

Indicate if the haproxy service is active. 



**Returns:**
  True if the haproxy is running. 

---

<a href="../src/haproxy.py#L65"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `reconcile`

```python
reconcile(config: CharmConfig) → None
```

Render the haproxy config and reload the haproxy service. 



**Args:**
 
 - <b>`config`</b>:  charm config 


---

## <kbd>class</kbd> `HaproxyServiceReloadError`
Error when reloading the haproxy service. 





