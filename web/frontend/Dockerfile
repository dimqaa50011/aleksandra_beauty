# ЭТАП 1: Сборка Vue-приложения
FROM node:20-alpine as build-stage
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
# Собираем проект (создастся папка dist)
RUN npm run build

# ЭТАП 2: Раздача через Nginx
FROM nginx:alpine as production-stage
# Копируем наш конфиг Nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf
# Копируем собранные файлы из первого этапа
COPY --from=build-stage /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]