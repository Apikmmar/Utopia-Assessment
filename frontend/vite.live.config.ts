import { mergeConfig } from "vite";
import baseConfig from "./vite.config";

export default mergeConfig(baseConfig, {
  server: { port: 5174, proxy: { "/api": { target: "http://127.0.0.1:8765" } } },
});
