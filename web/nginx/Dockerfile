FROM nginx:1.25-alpine

# Удаляем стандартный конфиг
RUN rm /etc/nginx/conf.d/default.conf

# Копируем наш конфиг
COPY nginx.conf /etc/nginx/conf.d/