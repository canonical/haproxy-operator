<!-- markdownlint-disable -->

<a href="../src/http_interface.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `http_interface.py`
The haproxy http interface module. 

**Global Variables**
---------------
- **SERVICES_CONFIGURATION_KEY**


---

## <kbd>class</kbd> `HTTPBackendAvailableEvent`
Event representing that http data has been provided. 





---

## <kbd>class</kbd> `HTTPBackendRemovedEvent`
Event representing that http data has been removed. 





---

## <kbd>class</kbd> `HTTPProvider`
HTTP interface provider class to be instantiated by the haproxy-operator charm. 

<a href="../src/http_interface.py#L49"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `__init__`

```python
__init__(charm: CharmBase, relation_name: str)
```

Initialize the interface base class. 



**Args:**
 
 - <b>`charm`</b>:  The charm implementing the requirer or provider. 
 - <b>`relation_name`</b>:  Name of the integration using the interface. 


---

#### <kbd>property</kbd> bind_address

Get Unit bind address. 



**Returns:**
  The unit address, or an empty string if no address found. 

---

#### <kbd>property</kbd> model

Shortcut for more simple access the model. 

---

#### <kbd>property</kbd> relations

The list of Relation instances associated with the charm. 




---

## <kbd>class</kbd> `HTTPRequirer`
HTTP interface provider class to be instantiated by the haproxy-operator charm. 

Attrs:  on: Custom events that are used to notify the charm using the provider.  services: Current services definition parsed from relation data. 

<a href="../src/http_interface.py#L123"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `__init__`

```python
__init__(charm: CharmBase, relation_name: str)
```

Initialize the HTTPRequirer class and parse the relation data. 



**Args:**
 
 - <b>`charm`</b>:  The charm instance 
 - <b>`relation_name`</b>:  The name of the relation 


---

#### <kbd>property</kbd> bind_address

Get Unit bind address. 



**Returns:**
  The unit address, or an empty string if no address found. 

---

#### <kbd>property</kbd> model

Shortcut for more simple access the model. 

---

#### <kbd>property</kbd> relations

The list of Relation instances associated with the charm. 


---

#### <kbd>handler</kbd> on


---

<a href="../src/http_interface.py#L169"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `get_services_definition`

```python
get_services_definition() → dict
```

Augment services_dict with service definitions from relation data. 



**Returns:**
  A dictionary containing the definition of all services. 


---

## <kbd>class</kbd> `HTTPRequirerEvents`
Container for HTTP Provider events. 

Attrs:  http_backend_available: Custom event when integration data is provided.  http_backend_removed: Custom event when integration data is removed. 


---

#### <kbd>property</kbd> model

Shortcut for more simple access the model. 




