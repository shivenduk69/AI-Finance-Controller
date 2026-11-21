FROM node:22-alpine

WORKDIR /app

# Install build dependencies if native addons require them
RUN apk add --no-cache python3 make g++

COPY package*.json ./

RUN npm install --omit=dev

COPY . .

EXPOSE 5000

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:5000/api/health || exit 1

CMD ["node", "server.js"]
