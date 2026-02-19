FROM golang:1.22-alpine AS build
WORKDIR /src
COPY go.mod /src/go.mod
COPY cmd /src/cmd
COPY internal /src/internal
RUN go build -o /out/pepoapple-agent ./cmd/agent

FROM alpine:3.20
RUN apk add --no-cache ca-certificates
COPY --from=build /out/pepoapple-agent /usr/local/bin/pepoapple-agent
ENTRYPOINT ["/usr/local/bin/pepoapple-agent"]
