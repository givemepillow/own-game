# these will speed up builds, for docker-compose >= 1.25
export COMPOSE_DOCKER_CLI_BUILD=1
export DOCKER_BUILDKIT=1

all: build up

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down --remove-orphans

logs:
	docker compose logs app

update:
	docker compose down --remove-orphans; docker image rm kirilllapushinskiy/own-game-bot; docker compose build; docker compose up -d
