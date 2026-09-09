#!/bin/bash
set -e

CERTS_DIR="./certs"
mkdir -p "$CERTS_DIR"
cd "$CERTS_DIR"

echo "=== Generazione Autorità di Certificazione (CA) ==="
openssl req -new -x509 -days 3650 -nodes -out ca.crt -keyout ca.key \
  -subj "/C=IT/ST=Rome/L=Rome/O=SmartFarm/CN=FarmCA"

echo "=== Creazione File di Configurazione OpenSSL con SAN ==="
cat <<EOF > openssl.cnf
[req]
default_bits = 2048
prompt = no
default_md = sha256
req_extensions = req_ext
distinguished_name = dn

[dn]
C = IT
ST = Rome
L = Rome
O = SmartFarm
CN = farm-brokers

[req_ext]
subjectAltName = @alt_names

[alt_names]
DNS.1 = mqtt-broker
DNS.2 = rabbitmq
DNS.3 = localhost
IP.1 = 127.0.0.1
EOF

echo "=== Generazione Chiave Privata e CSR ==="
openssl req -new -nodes -out server.csr -keyout server.key -config openssl.cnf

echo "=== Firma del Certificato con la CA ==="
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out server.crt -days 3650 -extensions req_ext -extfile openssl.cnf

# Configurazione permessi
chmod 644 ca.crt server.crt
chmod 600 ca.key server.key
rm -f server.csr openssl.cnf

echo "=== Certificati generati con successo nella cartella /certs ==="