FROM maven:3.9.9-eclipse-temurin-21 AS builder
WORKDIR /build
COPY pom.xml .
RUN mvn -q -e -U -B dependency:go-offline
COPY src ./src
RUN mvn -q -e -B clean package -DskipTests

FROM eclipse-temurin:21-jre-alpine

# bash 설치
RUN apk add --no-cache bash

ENV JAVA_OPTS=""
WORKDIR /app

# JAR 복사
COPY --from=builder /build/target/*SNAPSHOT.jar app.jar

# wait-for-it.sh 복사 및 실행권한 부여
COPY wait-for-it.sh wait-for-it.sh
RUN chmod +x wait-for-it.sh

# Drop privileges
RUN addgroup -S appgroup && adduser -S appuser -G appgroup \
    && chown -R appuser:appgroup /app
USER appuser

EXPOSE 8080

# 프로파일 환경 변수 추가
ENV SPRING_PROFILES_ACTIVE=docker

# db 준비될 때까지 대기 후 Spring 실행
ENTRYPOINT ["bash", "./wait-for-it.sh", "db:3306", "--timeout=60", "--strict", "--", "java", "-jar", "/app/app.jar"]