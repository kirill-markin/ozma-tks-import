#!/bin/bash

pwd
whoami

apt-get update

# Docker install and run
if [ "$1" != "-r" ]; then
  apt -y install docker.io docker-compose
  systemctl start docker
  systemctl enable docker
fi

docker-compose down
docker-compose build
docker-compose up &
