#### Basic setup

Start a PostgreSQL database:

```
docker run -d --name postgres -p 127.0.0.1:5432:5432 -e POSTGRES_PASSWORD=postgres -e POSTGRES_USERNAME=postgres postgres:latest
```

Basic snap configurations:

```
sudo snap set haproxy-route-policy database-password=postgres
sudo snap set haproxy-route-policy database-host=localhost
sudo snap set haproxy-route-policy database-port=5432
sudo snap set haproxy-route-policy database-user=postgres
sudo snap set haproxy-route-policy database-name=postgres
```

## Learn more
* [Read more](https://documentation.ubuntu.com/haproxy-charm/latest/)

## Project and community
* [Issues](https://github.com/canonical/haproxy-operator/issues)
* [Matrix](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)
