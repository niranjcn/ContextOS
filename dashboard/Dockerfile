# ==============================================================================
# ContextOS Dashboard — Multi-Stage Dockerfile
# ==============================================================================
# Stage 1: Build the React app with Vite (produces static files in /app/dist)
# Stage 2: Serve the built files with nginx (tiny ~25MB final image)
# ==============================================================================

# ---------------------------------------------------------------------------
# STAGE 1 — Build: compile React/JSX into optimized static assets
# ---------------------------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files first for Docker layer caching.
# npm ci only re-runs if package.json or package-lock.json change.
COPY package*.json ./

# npm ci (clean install) is preferred over npm install for CI/Docker:
# - Uses exact versions from package-lock.json (reproducible builds)
# - Faster than npm install (skips dependency resolution)
# - Fails if package-lock.json is out of sync (catches mistakes)
RUN npm ci

# Now copy the rest of the source code
COPY . .

# Build the production bundle. Vite outputs to /app/dist by default.
# This tree-shakes, minifies, and optimizes all JS/CSS.
RUN npm run build

# ---------------------------------------------------------------------------
# STAGE 2 — Runtime: serve static files with nginx
# ---------------------------------------------------------------------------
FROM nginx:alpine

# Copy the built React app from the builder stage into nginx's
# default serving directory.
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy our custom nginx config that handles:
# - React Router (SPA fallback to index.html)
# - API reverse proxy (/api/* → backend)
# - Gzip compression
# - Browser caching headers
COPY nginx.conf /etc/nginx/conf.d/default.conf

# nginx listens on port 80 by default
EXPOSE 80

# nginx runs in the foreground (daemon off is the default in the
# official nginx Docker image, so no extra config needed).
CMD ["nginx", "-g", "daemon off;"]
