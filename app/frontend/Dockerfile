# Frontend image. Three results come out of this file:
#   dev     what Docker Compose runs on the laptop: the Vite dev server with hot reload
#   build   runs the production build; its dist/ folder is what B3 uploads to S3
#   static  a small web server with the built files, for the Kubernetes lab and for
#           trying the production build locally
#
# AWS never runs a frontend container: there the files are served from S3 by CloudFront.
#
# Images are pinned by digest (SR-80). Dependabot updates the lines below.

FROM node:26.13.0-trixie-slim@sha256:5adad64f9a1fca2d51972caa65983634c8a774eb300d72b20f7f2a0f60368072 AS node-base

# npm's cache and logs go to /tmp, the only writable place when the container runs.
ENV NPM_CONFIG_CACHE=/tmp/npm \
    NPM_CONFIG_UPDATE_NOTIFIER=false \
    NPM_CONFIG_FUND=false \
    HOME=/tmp \
    PATH=/app/node_modules/.bin:$PATH

WORKDIR /app

# ---- deps: the packages, exactly as locked ------------------------------------
FROM node-base AS deps

COPY package.json package-lock.json .npmrc ./

# npm ci installs exactly what package-lock.json says and fails if package.json
# disagrees with it. It never changes the lockfile. (.npmrc switches install scripts off.)
# --mount=type=cache: the download cache is kept between builds, not in the image.
RUN --mount=type=cache,target=/tmp/npm \
    npm ci

# ---- dev: for Docker Compose ---------------------------------------------------
FROM deps AS dev

# The source is not copied in. Compose mounts it from the laptop, so edits show at once.
# 1000 is "node", the non-root user that the official image provides. The number is
# used instead of the name so Kubernetes can check that it is not 0 (root).
USER 1000:1000
EXPOSE 5173
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
    CMD ["node", "-e", "fetch('http://127.0.0.1:5173/').then(r => process.exit(r.ok ? 0 : 1), () => process.exit(1))"]
# --configLoader runner: load vite.config.ts without writing a temporary file; the
# container's file system is read-only.
CMD ["vite", "--configLoader", "runner", "--host", "0.0.0.0"]

# ---- build: the production build -------------------------------------------------
FROM deps AS build

COPY index.html tsconfig.json vite.config.ts ./
COPY src ./src

# Type errors stop the build; then Vite writes the finished site to /app/dist.
RUN tsc --noEmit && vite build --configLoader runner

# ---- static: the built files behind a small web server ------------------------------
# nginx-unprivileged is nginx set up to run as a non-root user (uid 101) on port 8080.
FROM nginxinc/nginx-unprivileged:1.30.6-alpine-slim@sha256:5d8bb9437d74a600ec5dbf90c035451c724dc33eac8d3a71078f6f8612c345f6 AS static

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

USER 101:101
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD ["wget", "--quiet", "--spider", "http://127.0.0.1:8080/"]
