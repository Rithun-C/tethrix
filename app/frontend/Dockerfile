# Frontend image. Three results come out of this file:
#   dev     what Docker Compose runs on the laptop: the Vite dev server with hot reload
#   build   runs the production build; its dist/ folder is what B3 uploads to S3
#   static  a small web server with the built files, for the Kubernetes lab and for
#           trying the production build locally
#
# AWS never runs a frontend container: there the files are served from S3 by CloudFront.
#
# Images are pinned by digest (SR-80). Dependabot updates the lines below.

FROM node:26.13.1-trixie-slim@sha256:e6bedef217677b276c591795e169840edd9096dbf13f29df8ef8d1856b8820bc AS node-base

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

# ---- dist: only the built files, for `make frontend-dist` ----------------------------
# An image that holds nothing but the contents of /app/dist. It is never run:
# `docker build --target dist --output type=local,dest=...` copies the files out to the
# laptop, and the backend image build copies them in (ADR-0007). Without this stage,
# --output would copy the whole build stage, node_modules included.
FROM scratch AS dist
COPY --from=build /app/dist /

# ---- static: the built files behind a small web server ------------------------------
# nginx-unprivileged is nginx set up to run as a non-root user (uid 101) on port 8080.
# 1.31 is nginx's mainline line. In November 2026 the stable line (1.30) had no rebuilt
# image with the fixes for six HTTP/2, HTTP/3 and resolver bugs (F-020); 1.31.7 has them.
FROM nginxinc/nginx-unprivileged:1.31.7-alpine-slim@sha256:a8cb0f33d51fa107c96fd2bd3a71aaf564ec131e9d2bdf8700944f0ed8b170d7 AS static

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

USER 101:101
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD ["wget", "--quiet", "--spider", "http://127.0.0.1:8080/"]
