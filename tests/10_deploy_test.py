#!/usr/bin/python3

# This Amulet test deploys haproxy and related charms.

import os
import amulet
import requests
import base64
import yaml
import time

d = amulet.Deployment(series='trusty')
# Add the haproxy charm to the deployment.
d.add('haproxy')
d.add('apache2')

# Get the directory this way to load the file when CWD is different.
path = os.path.abspath(os.path.dirname(__file__))
template_path = os.path.join(path, 'default_apache.tmpl')
# Read in the Apache2 default template file.
with open(template_path) as f:
    template = f.read()
    encodedTemplate = base64.b64encode(template.encode('utf-8'))
# Create a dictionary with configuration values for apache2.
configuration = {'vhost_http_template': encodedTemplate.decode('ascii')}
# Apache2 needs a base64 encoded template to configure the web site.
d.configure('apache2', configuration)

# Relate the haproxy to apache2.
d.relate('haproxy:reverseproxy', 'apache2:website')
# Make the haproxy visible to the outside world.
d.expose('haproxy')

# The number of seconds to wait for the environment to setup.
seconds = 900
try:
    # Execute the deployer with the current mapping.
    d.setup(timeout=seconds)
    # Wait for the relation to finish the transations.
    d.sentry.wait(seconds)
except amulet.helpers.TimeoutError:
    message = 'The environment did not setup in %d seconds.' % seconds
    # The SKIP status enables skip or fail the test based on configuration.
    amulet.raise_status(amulet.SKIP, msg=message)
except:
    raise

# Test that haproxy is acting as the proxy for apache2.

# Get the haproxy unit.
haproxy_unit = d.sentry.unit['haproxy/0']
haproxy_address = haproxy_unit.info['public-address']
page = requests.get('http://%s/index.html' % haproxy_address)
# Raise an error if the page does not load through haproxy.
page.raise_for_status()
print('Successfully got the Apache2 web page through haproxy IP address.')

# Test that sticky session cookie is present
if page.cookies.get('SRVNAME') != 'S0':
    msg = 'Missing or invalid sticky session cookie value: %s' % page.cookies.get('SRVNAME')
    amulet.raise_status(amulet.FAIL, msg=msg)

# Test that the apache2 relation data is saved on the haproxy server.

# Get the sentry for apache and get the private IP address.
apache_unit = d.sentry.unit['apache2/0']
# Get the relation.
relation = apache_unit.relation('website', 'haproxy:reverseproxy')
# Get the private address from the relation.
apache_private = relation['private-address']

print('Private address of the apache2 relation ', apache_private)

# Grep the configuration file for the private address
output, code = haproxy_unit.run('grep %s /etc/haproxy/haproxy.cfg' %
                                apache_private)
if code == 0:
    print('Found the relation IP address in the haproxy configuration file!')
    print(output)
else:
    print(output)
    message = 'Unable to find the Apache IP address %s in the haproxy ' \
              'configuration file.' % apache_private
    amulet.raise_status(amulet.FAIL, msg=message)

d.configure('haproxy', {
    'source': 'backports',
    'ssl_cert': 'SELFSIGNED',
    'services': yaml.safe_dump([
        {'service_name': 'apache',
         'service_host': '0.0.0.0',
         'service_port': 80,
         'service_options': [
             'mode http', 'balance leastconn', 'option httpchk GET / HTTP/1.0'
         ],
         'servers': [
             ['apache', apache_private, 80, 'maxconn 50']]},
        {'service_name': 'apache-ssl',
         'service_port': 443,
         'service_host': '0.0.0.0',
         'service_options': [
             'mode http', 'balance leastconn', 'option httpchk GET / HTTP/1.0'
         ],
         'crts': ['DEFAULT'],
         'servers': [['apache', apache_private, 80, 'maxconn 50']]}])
})

# We need a retry loop here, since there's no way to tell when the new
# configuration is in place.
url = 'https://%s/index.html' % haproxy_address
retries = 10
for i in range(retries):
    try:
        page = requests.get(url, verify=False)
        page.raise_for_status()
    except requests.exceptions.ConnectionError:
        if i == retries - 1:
            # This was the last one, let's fail
            raise
        time.sleep(6)
    else:
        break

print('Successfully got the Apache2 web page through haproxy SSL termination.')

# Send a message that the tests are complete.
print('The haproxy tests are complete.')
