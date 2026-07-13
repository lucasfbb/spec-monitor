# Build do frontend (TanStack Start → nitro node-server) e runtime Node enxuto.
FROM node:22-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# VITE_API_URL entra em build time (é embutido no bundle do cliente). Vazio =
# chamadas relativas /api (mesma origem, via reverse proxy). Ver docs/deploy.
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM node:22-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production
# Só o output do nitro é necessário em runtime (traz as deps embutidas).
COPY --from=build /app/.output ./.output
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser
EXPOSE 3000
ENV PORT=3000
CMD ["node", ".output/server/index.mjs"]
