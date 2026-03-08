#!/bin/bash
# OpenAPI 定義を Frontend にコピー
cd "$(dirname "$0")/.."
[ -d Frontend ] || exit 0
mkdir -p Frontend/docs
cp docs/openapi_*.yaml Frontend/docs/
