FROM node:20-alpine

WORKDIR /workspace

RUN corepack enable && corepack prepare pnpm@9.12.3 --activate

CMD ["sh", "-c", "pnpm install --no-frozen-lockfile && pnpm --filter @waifu-tutor/frontend dev --host 0.0.0.0 --port 5173"]
