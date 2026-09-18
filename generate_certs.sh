#!/usr/bin/env bash
set -Eeuo pipefail

CERT_DIR="${CERT_DIR:-certs}"
BROKER_HOST="${BROKER_HOST:-mqtt-broker}"

CA_KEY="$CERT_DIR/ca.key"
CA_CERT="$CERT_DIR/ca.crt"
SERVER_KEY="$CERT_DIR/server.key"
SERVER_CSR="$CERT_DIR/server.csr"
SERVER_CERT="$CERT_DIR/server.crt"
OPENSSL_CONFIG="$CERT_DIR/openssl.cnf"
SERIAL_FILE="$CERT_DIR/ca.srl"

pause_if_interactive() {
    if [ -t 0 ]; then
        printf "\nPremi Invio per chiudere..."
        read -r _
    fi
}

on_error() {
    exit_code=$?
    printf "\nERRORE: generazione certificati fallita.\n" >&2
    printf "Linea: %s\n" "${BASH_LINENO[0]:-sconosciuta}" >&2
    printf "Comando: %s\n" "${BASH_COMMAND:-sconosciuto}" >&2
    printf "Codice uscita: %s\n" "$exit_code" >&2
    printf "\nControllare il messaggio OpenSSL riportato sopra.\n" >&2
    pause_if_interactive
    exit "$exit_code"
}

trap on_error ERR

printf "========================================\n"
printf " Smart Farm - Generazione certificati\n"
printf "========================================\n\n"

if ! command -v openssl >/dev/null 2>&1; then
    printf "ERRORE: OpenSSL non e' installato o non e' nel PATH.\n" >&2
    printf "\nLinux/WSL (Ubuntu/Debian):\n"
    printf "  sudo apt update && sudo apt install openssl\n"
    printf "\nWindows:\n"
    printf "  eseguire lo script da Git Bash/WSL con OpenSSL disponibile.\n"
    pause_if_interactive
    exit 1
fi

printf "OpenSSL: "
openssl version

mkdir -p "$CERT_DIR"

# Tutti i distinguished name sono definiti qui.
# Evitiamo intenzionalmente `openssl ... -subj "/CN=..."` perché Git Bash/MSYS
# può convertire `/CN=...` in un percorso Windows (es. C:/Program Files/Git/CN=...).
cat > "$OPENSSL_CONFIG" <<EOF
[ca_req]
prompt = no
distinguished_name = ca_dn
x509_extensions = ca_ext

[ca_dn]
CN = Smart Farm Local CA

[ca_ext]
basicConstraints = critical, CA:true
keyUsage = critical, keyCertSign, cRLSign
subjectKeyIdentifier = hash

[server_req]
prompt = no
distinguished_name = server_dn
req_extensions = server_req_ext

[server_dn]
CN = ${BROKER_HOST}

[server_req_ext]
subjectAltName = @alt_names

[server_cert_ext]
basicConstraints = critical, CA:false
subjectAltName = @alt_names
extendedKeyUsage = serverAuth
keyUsage = critical, digitalSignature, keyEncipherment
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid,issuer

[alt_names]
DNS.1 = ${BROKER_HOST}
DNS.2 = localhost
IP.1 = 127.0.0.1
EOF

printf "\n[1/6] Generazione chiave privata CA...\n"
openssl genrsa \
    -out "$CA_KEY" \
    4096

printf "[2/6] Generazione certificato CA...\n"
openssl req \
    -x509 \
    -new \
    -sha256 \
    -key "$CA_KEY" \
    -days 3650 \
    -config "$OPENSSL_CONFIG" \
    -section ca_req \
    -out "$CA_CERT"

printf "[3/6] Generazione chiave privata broker...\n"
openssl genrsa \
    -out "$SERVER_KEY" \
    2048

printf "[4/6] Generazione richiesta certificato broker...\n"
openssl req \
    -new \
    -key "$SERVER_KEY" \
    -out "$SERVER_CSR" \
    -config "$OPENSSL_CONFIG" \
    -section server_req

printf "[5/6] Firma certificato broker...\n"
openssl x509 \
    -req \
    -in "$SERVER_CSR" \
    -CA "$CA_CERT" \
    -CAkey "$CA_KEY" \
    -CAcreateserial \
    -out "$SERVER_CERT" \
    -days 825 \
    -sha256 \
    -extensions server_cert_ext \
    -extfile "$OPENSSL_CONFIG"

printf "[6/6] Verifica certificato...\n"
openssl verify \
    -CAfile "$CA_CERT" \
    "$SERVER_CERT"

for file in "$CA_KEY" "$CA_CERT" "$SERVER_KEY" "$SERVER_CERT"; do
    if [ ! -s "$file" ]; then
        printf "ERRORE: file non generato o vuoto: %s\n" "$file" >&2
        false
    fi
done

printf "\nSubject Alternative Name del broker:\n"
openssl x509 \
    -in "$SERVER_CERT" \
    -noout \
    -ext subjectAltName

printf "\nSubject CA:\n"
openssl x509 \
    -in "$CA_CERT" \
    -noout \
    -subject

printf "\nSubject broker:\n"
openssl x509 \
    -in "$SERVER_CERT" \
    -noout \
    -subject

rm -f \
    "$SERVER_CSR" \
    "$OPENSSL_CONFIG" \
    "$SERIAL_FILE"

# Su filesystem Unix questi permessi sono applicati realmente.
# Su alcuni filesystem Windows chmod può non avere effetto: non rendiamo
# invalida una generazione TLS corretta solo per questo motivo.
chmod 600 "$CA_KEY" "$SERVER_KEY" 2>/dev/null || true
chmod 644 "$CA_CERT" "$SERVER_CERT" 2>/dev/null || true

printf "\n========================================\n"
printf " Certificati generati correttamente\n"
printf "========================================\n"
printf "CA privata:          %s\n" "$CA_KEY"
printf "CA pubblica:         %s\n" "$CA_CERT"
printf "Chiave broker:       %s\n" "$SERVER_KEY"
printf "Certificato broker:  %s\n" "$SERVER_CERT"
printf "Hostname TLS:        %s\n" "$BROKER_HOST"
printf "\nNON aggiungere *.key al repository Git.\n"

pause_if_interactive
