# Multi-stage build for PAM DX Portal
FROM maven:3.9-eclipse-temurin-17-alpine AS build
WORKDIR /app
COPY pom.xml .
RUN mvn dependency:go-offline -B
COPY src src
RUN mvn package -DskipTests -B

FROM eclipse-temurin:17-jre-alpine
WORKDIR /app
COPY --from=build /app/target/pam-dx-portal-*.jar app.jar

# Non-root user
RUN addgroup -S pamdx && adduser -S pamdx -G pamdx
USER pamdx

EXPOSE 8443

ENTRYPOINT ["java", "-jar", "app.jar"]
