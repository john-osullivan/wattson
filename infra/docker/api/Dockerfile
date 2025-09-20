FROM node:20-slim
WORKDIR /app
COPY ../../api/package.json /app/package.json
COPY ../../api/src /app/src
RUN npm install --omit=dev
EXPOSE 8088
CMD ["node","src/pr.js"]
