FROM node:20-alpine AS build

WORKDIR /workspace

COPY package.json /workspace/package.json
COPY package-lock.json /workspace/package-lock.json
COPY apps/web/package.json /workspace/apps/web/package.json
COPY packages/shared/package.json /workspace/packages/shared/package.json
RUN npm install

COPY tsconfig.base.json /workspace/tsconfig.base.json
COPY packages/shared /workspace/packages/shared
COPY apps/web /workspace/apps/web

RUN npm run build --workspace=@podiumforge/web

FROM nginx:1.27-alpine

COPY apps/web/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=build /workspace/apps/web/dist /usr/share/nginx/html

EXPOSE 80
