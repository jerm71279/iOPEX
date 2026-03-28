# PAM DX Portal

Java/Spring Boot portal for PAM digital experience — client-facing web interface for migration status and self-service.

## Stack
- **Language**: Java (Spring Boot)
- **Build**: Maven (`pom.xml`)
- **Container**: Docker (`Dockerfile`, `docker-compose.yml`)
- **Documentation**: `docs/`

## Key Files
```
src/
  main/
    java/         Java source (Spring Boot application)
    resources/    application.properties, templates
pom.xml           Maven build config
Dockerfile        Container image definition
docker-compose.yml  Local dev stack
docs/             API and integration documentation
```

## Run Commands
```bash
# Local dev
mvn spring-boot:run

# Build JAR
mvn clean package -DskipTests

# Docker
docker-compose up --build
```

## Environment Variables
See `.env` — Spring Boot reads from environment; configure DB, auth, and service URLs.
