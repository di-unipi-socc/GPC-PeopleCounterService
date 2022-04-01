# GiòPeopleCounter - PeopleCounterService

A RESTful Cloud service to collect and render people counts obtained from [GPC-MonitoringUnit](https://github.com/di-unipi-socc/GPC-MonitoringUnit)s.

The PeopleCounterService features a GUI and database to store detected count events from multiple monitoring units installed at the entrance doors of a builiding. The service can be launched through Docker in swarm mode.
___

## Modules 

The PeopleCounterService is composed of three main components: the Collector service, the API gateway service and the DB service.

### Collector Service
It is the main backend service wrapping all requests towards the database and rendering information through a GUI.
Is composed of the following modules:
- configs: configuration files, to be filled in with deployment configurations,
- db: classes for handling interactions with the database,
- endpoints: all classes used by endpoints to handle requests,
- net_io: implements network interactions, e.g. sockets, notification handling.
- static: contains all static files to serve the clients,
- templates: GUI views,
- utils: utility functions and classes used to manage provided services, and
- app: main application module.

### API Gateway Service
Gateway/Load-Balancer service, that act as Proxy between services and clients.

### DB Service
Provide the DBMS for Counts Estimation Storage.

___
## Deployment instructions

### 1) Docker/Docker Swarm install
Install on server-machine, Docker and Docker-Swarm

### 2) Server PKI keys/pub_certificates
Create Server certificates from a Reliable Certification Authority.
Copy the obtained certificates inside collector/app and haproxy_img folders, and set right parameters-path to let services to use them.

### 3) Edit configuration files
Starting from the provided templates, fill in configuration files, setting all required parameters.

The configs files to produce are:
- Collector-Service configurations: 
  - collector/app/configs/config.py and secrets_conf.py
  - collector/app/gunicorn.conf.py
- Gateway/Load-balancer configuration: haproxy_img/haproxy.cfg
- Docker_compose files:
  - gio_counter_deploy.yaml
  - pg-secrets.env
  - collector-secrets.env

### 4) Build Collector and Gateway Images
From project folders, build images for the Collector and Gateway Services.
The dockerfiles are in the folders: collector/ and haproxy_img/
Issue the commands:

```bash
docker build -t collector/ collector
docker build -t haproxy_img/ gio_haproxy
```

### 4) Deploy the Swarm:
```bash
docker stack deploy -c compose_file.yaml Swarm-App-Name
```

