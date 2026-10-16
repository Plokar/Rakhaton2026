# IRIS for Health (FHIR R4 + Vector Search), převzato z FHIR-AI-Hackathon-Kit V2 docker-iris-fhir
# 2026.2 = latest-cd k 16. 10. 2026 (ARCH §4.2: zafixovaný tag)
FROM intersystems/irishealth-community:2026.2

COPY merge.cpf /tmp/merge.cpf

USER root
RUN mkdir -p /durable && chown irisowner:irisowner /durable
USER irisowner

# CallIn služba pro DB-API / native API; hesla bez expirace (jinak REST vrací 401 do první změny)
RUN iris start IRIS && \
    iris merge IRIS /tmp/merge.cpf && \
    echo 'do ##class(Security.Users).UnExpireUserPasswords("*")' | iris session IRIS -U %SYS && \
    iris stop IRIS quietly
