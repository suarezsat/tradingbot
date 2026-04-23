import { Container, getContainer } from "@cloudflare/containers";

export class TradingbotContainer extends Container {
  defaultPort = 8501;
  sleepAfter = "30m";
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/__health") {
      return new Response("ok", {
        headers: {
          "content-type": "text/plain; charset=utf-8"
        }
      });
    }

    return getContainer(env.TRADINGBOT_CONTAINER, "app").fetch(request);
  }
};
