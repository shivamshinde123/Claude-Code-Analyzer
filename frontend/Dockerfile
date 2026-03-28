FROM node:20-slim AS builder

WORKDIR /app

# Copy dependency files first for layer caching
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci

# Copy source code and build
COPY index.html vite.config.js ./
COPY src/ src/
COPY public/ public/

RUN npm run build

# Production stage — serve the static build with a lightweight HTTP server
FROM node:20-slim

WORKDIR /app

RUN npm install -g serve

COPY --from=builder /app/dist ./dist

EXPOSE 5173

CMD ["serve", "-s", "dist", "-l", "5173"]
