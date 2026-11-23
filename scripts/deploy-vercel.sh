#!/bin/sh
# Build the web app and deploy it together with the API to https://devoppers.vercel.app
set -e
cd "$(dirname "$0")/.."
rm -rf backend/public
EXPO_PUBLIC_API_BASE_URL=https://devoppers.vercel.app npx expo export --platform web --output-dir backend/public
cd backend
vercel deploy --prod --yes
