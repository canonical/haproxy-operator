<!-- markdownlint-disable -->

<a href="../src/tls_relation.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `tls_relation.py`
Haproxy TLS relation business logic. 

**Global Variables**
---------------
- **TLS_CERT**

---

<a href="../src/tls_relation.py#L51"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `get_hostname_from_cert`

```python
get_hostname_from_cert(certificate: str) → str
```

Get the hostname from a certificate subject name. 



**Args:**
 
 - <b>`certificate`</b>:  The certificate in PEM format. 



**Returns:**
 The hostname the certificate is issue to. 



**Raises:**
 
 - <b>`InvalidCertificateError`</b>:  When hostname cannot be parsed from the given certificate. 


---

## <kbd>class</kbd> `GetPrivateKeyError`
Exception raised when the private key secret doesn't exist. 





---

## <kbd>class</kbd> `InvalidCertificateError`
Exception raised when certificates is invalid. 





---

## <kbd>class</kbd> `KeyPair`
Stores a private key and encryption password. 



**Attributes:**
 
 - <b>`private_key`</b>:  The private key 
 - <b>`password`</b>:  The password used for encryption 





---

## <kbd>class</kbd> `TLSRelationService`
TLS Relation service class. 

<a href="../src/tls_relation.py#L82"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `__init__`

```python
__init__(model: Model, certificates: TLSCertificatesRequiresV3) → None
```

Init method for the class. 



**Args:**
 
 - <b>`model`</b>:  The charm's current model. 
 - <b>`certificates`</b>:  The TLS certificates requirer library. 




---

<a href="../src/tls_relation.py#L253"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `all_certificate_invalidated`

```python
all_certificate_invalidated() → None
```

Clean up certificates in unit and private key secrets. 

---

<a href="../src/tls_relation.py#L242"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `certificate_available`

```python
certificate_available(certificate: str) → None
```

Handle TLS Certificate available event. 



**Args:**
 
 - <b>`certificate`</b>:  The provided certificate. 

---

<a href="../src/tls_relation.py#L182"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `certificate_expiring`

```python
certificate_expiring(certificate: str) → None
```

Handle the TLS Certificate expiring event. 

Generate a new CSR and request for a new certificate. 



**Args:**
 
 - <b>`certificate`</b>:  The invalidated certificate. 

---

<a href="../src/tls_relation.py#L205"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `certificate_invalidated`

```python
certificate_invalidated(
    certificate: Optional[str] = None,
    provider_certificate: Optional[ProviderCertificate] = None
) → None
```

Handle TLS Certificate revocation. 



**Args:**
 
 - <b>`certificate`</b>:  The invalidated certificate to match with a provider certificate. 
 - <b>`provider_certificate`</b>:  The provider certificate, skip certificate matching if this is provided directly. 

---

<a href="../src/tls_relation.py#L94"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `generate_password`

```python
generate_password() → str
```

Generate a random 12 character password. 



**Returns:**
 
 - <b>`str`</b>:  Private key string. 

---

<a href="../src/tls_relation.py#L118"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `generate_private_key`

```python
generate_private_key(hostname: str) → None
```

Handle the TLS Certificate created event. 



**Args:**
 
 - <b>`hostname`</b>:  Certificate's hostname. 

---

<a href="../src/tls_relation.py#L166"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `get_provider_cert_with_hostname`

```python
get_provider_cert_with_hostname(hostname: str) → Optional[ProviderCertificate]
```

Get a cert from the provider's integration data that matches 'certificate'. 



**Args:**
 
 - <b>`hostname`</b>:  the hostname to match with provider certificates 



**Returns:**
 
 - <b>`typing.Optional[ProviderCertificate]`</b>:  ProviderCertificate if exists, else None. 

---

<a href="../src/tls_relation.py#L274"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `remove_certificate_from_unit`

```python
remove_certificate_from_unit(hostname: str) → None
```

Remove the certificate having "hostname" from haproxy cert directory. 



**Args:**
 
 - <b>`hostname`</b>:  the hostname of the provider certificate. 

---

<a href="../src/tls_relation.py#L103"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `request_certificate`

```python
request_certificate(hostname: str) → None
```

Handle the TLS Certificate joined event. 



**Args:**
 
 - <b>`hostname`</b>:  Certificate's hostname. 

---

<a href="../src/tls_relation.py#L258"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `write_certificate_to_unit`

```python
write_certificate_to_unit(certificate: str) → None
```

Write the certificate having "hostname" to haproxy cert directory. 



**Args:**
 
 - <b>`certificate`</b>:  the certificate to write to the unit filesystem. 


