# ---- Base Node ----
FROM node:19-alpine AS base
RUN apk add --no-cache git
RUN git clone https://github.com/mckaywrigley/chatbot-ui /app && cd /app && git checkout 3f09a4c35549af678f429c1ec43b0fc8cd8ad280
WORKDIR /app
RUN sed -i -e 's/https:\/\/api.openai.com/http:\/\/chatbot:5000/g' ./utils/server/index.ts

# ---- Dependencies ----
FROM base AS dependencies
RUN npm ci

# ---- Build ----
FROM dependencies AS build

RUN npm run build

# ---- Production ----
FROM node:19-alpine AS production
WORKDIR /app
COPY --from=dependencies /app/node_modules ./node_modules
COPY --from=build /app/.next ./.next
COPY --from=build /app/public ./public
COPY --from=build /app/package*.json ./
COPY --from=build /app/next.config.js ./next.config.js
COPY --from=build /app/next-i18next.config.js ./next-i18next.config.js

# Expose the port the app will run on
EXPOSE 3000

# Start the application
CMD ["npm", "start"]

