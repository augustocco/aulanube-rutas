#!/usr/bin/env bash
# Despliega AulaNube Rutas en el clúster K3s de la Unidad 1 (OCI).
# Construye la imagen arm64 en el nodo 1, la importa en ambos nodos y aplica el manifiesto.
# Requisito: la lista de seguridad de OCI debe permitir SSH desde la IP pública actual.
set -euo pipefail
NODO1="${NODO1:-ubuntu@149.130.191.139}"
NODO2="${NODO2:-ubuntu@157.137.224.145}"
LLAVE="${LLAVE:-$HOME/.ssh/id_rsa}"
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
ssh1() { ssh -i "$LLAVE" "$NODO1" "$@"; }
ssh2() { ssh -i "$LLAVE" "$NODO2" "$@"; }

echo "→ Copiando el código al nodo 1"
tar -C "$RAIZ" --exclude='__pycache__' -czf - Dockerfile .dockerignore rutas infra \
  | ssh1 "rm -rf ~/rutas-build && mkdir -p ~/rutas-build && tar -xzf - -C ~/rutas-build"
echo "→ Construyendo aulanube/rutas:v1 (arm64 nativo)"
ssh1 "cd ~/rutas-build && sudo docker build -q -t aulanube/rutas:v1 . >/dev/null"
echo "→ Importando la imagen en containerd de ambos nodos"
ssh1 "sudo docker save aulanube/rutas:v1 | sudo k3s ctr -n k8s.io images import - >/dev/null"
ssh1 "sudo docker save aulanube/rutas:v1" | ssh2 "sudo k3s ctr -n k8s.io images import - >/dev/null"
echo "→ Aplicando el manifiesto"
ssh1 "sudo k3s kubectl apply -f ~/rutas-build/infra/k8s/rutas.yaml"
ssh1 "sudo k3s kubectl -n aulanube-rutas rollout restart deploy && sudo k3s kubectl -n aulanube-rutas rollout status deploy --timeout=180s"
echo "Iteración 3: https://rutas.149-130-191-139.sslip.io"
echo "Iteración 1: https://rutas-v1.149-130-191-139.sslip.io"
