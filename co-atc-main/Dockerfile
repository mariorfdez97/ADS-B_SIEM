FROM golang:1.23-alpine AS build

WORKDIR /src

RUN apk add --no-cache git

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN go build -o /out/co-atc ./cmd/server

FROM alpine:3.20

RUN apk add --no-cache ca-certificates tzdata

WORKDIR /app

COPY --from=build /out/co-atc /app/co-atc
COPY assets /app/assets
COPY www /app/www
COPY configs /app/configs

EXPOSE 8000

ENV COATC_CONFIG=/app/configs/config.docker.toml
CMD ["/app/co-atc", "-config", "/app/configs/config.docker.toml"]
