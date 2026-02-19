FROM node:22-alpine
WORKDIR /app
COPY package.json /app/package.json
COPY tsconfig.json next.config.ts postcss.config.js tailwind.config.ts next-env.d.ts /app/
COPY app /app/app
COPY components /app/components
COPY lib /app/lib
RUN npm install
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "start", "--", "--hostname", "0.0.0.0", "--port", "3000"]
