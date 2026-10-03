# E-commerce App: Vagrant + Docker Compose (volumes and networks)

A small online shop running in a VirtualBox VM managed by Vagrant. Docker Compose runs four containers.

```
Browser ──► web (Nginx) ──► api (Flask) ──┬──► db (PostgreSQL)
            frontend-net     frontend-net  └──► redis (cart cache)
                             + backend-net    backend-net (internal)
```

| Service | Image | Role | Volume |
|---------|-------|------|--------|
| web   | nginx:1.27-alpine (custom) | Shop page, reverse proxy for `/api/` | `nginx_logs` |
| api   | python:3.12-slim (custom)  | Products, cart, checkout, orders | none |
| db    | postgres:16-alpine | Products, orders, order items | `pgdata` |
| redis | redis:7-alpine | Shopping carts (24h expiry) | `redisdata` |

## Networks
- `frontend-net`: web and api only.
- `backend-net` (`internal: true`): api, db and redis. No internet access, and nothing outside Docker can reach the database or Redis.

## Volumes
- `pgdata`, `redisdata`, `nginx_logs` are named volumes. Data survives `docker compose down` and container rebuilds. Only `docker compose down -v` deletes it.
- `db/init.sql` is bind-mounted into the database container and runs once on first start, creating tables and 6 sample products.

## Prerequisites
VirtualBox, Vagrant, Git.

## Run
```bash
git clone https://github.com/<your-username>/ecommerce-docker-vagrant.git
cd ecommerce-docker-vagrant
vagrant up
```
Open http://localhost:8081

## Try it
1. Add products to the cart and place an order.
2. Reload the page: the cart and orders are still there (Redis and PostgreSQL volumes).
3. Inside the VM (`vagrant ssh`, then `cd /vagrant`):
```bash
docker compose ps                     # 4 running containers
docker network ls                     # frontend-net, backend-net
docker volume ls                      # pgdata, redisdata, nginx_logs
docker compose exec db psql -U shopuser -d shopdb -c "SELECT * FROM orders;"
docker compose exec redis redis-cli keys '*'
docker compose down && docker compose up -d   # data is still there
docker compose exec web ls /var/log/nginx
```

## API
| Method | Path | Purpose |
|--------|------|---------|
| GET  | `/api/health` | Database and Redis status |
| GET  | `/api/products` | List products |
| GET/POST/DELETE | `/api/cart/<sid>` | View, add/remove items, clear cart |
| POST | `/api/checkout` | Create an order from the cart |
| GET  | `/api/orders` | Last 10 orders |

## Without Vagrant
```bash
cp .env.example .env
docker compose up -d --build     # http://localhost:8080
```

## Cleanup
```bash
vagrant halt          # stop the VM
vagrant destroy -f    # delete the VM
```
