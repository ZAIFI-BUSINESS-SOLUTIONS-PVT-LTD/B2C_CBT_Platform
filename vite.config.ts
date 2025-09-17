import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import os from "os";
import runtimeErrorOverlay from "@replit/vite-plugin-runtime-error-modal";

export default defineConfig({
  plugins: [
    react(),
    runtimeErrorOverlay(),
    // Plugin: print network IPs so other devices can connect to the dev server
    {
      name: "print-network-ips",
      configureServer(server) {
        // collect non-internal IPv4 addresses
        const interfaces = os.networkInterfaces();
        const ips: string[] = [];
        for (const name of Object.keys(interfaces)) {
          const nets = interfaces[name];
          if (!nets) continue;
          for (const net of nets) {
            if (net.family === "IPv4" && !net.internal) {
              ips.push(net.address);
            }
          }
        }

        // Wait until the underlying HTTP server is listening to get the active port
        server.httpServer?.once("listening", () => {
          // address() can return string or AddressInfo|null; guard it
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const addr: any = server.httpServer?.address();
          const port = (addr && typeof addr === "object" && addr.port) || server.config.server.port || 5173;
          if (ips.length > 0) {
            // print a compact list of network URLs
            console.log("\n  Dev server available on your local network:");
            for (const ip of ips) {
              console.log(`  http://${ip}:${port}/`);
            }
            console.log("");
          }
        });
      },
    },
    ...(process.env.NODE_ENV !== "production" &&
    process.env.REPL_ID !== undefined
      ? [
          await import("@replit/vite-plugin-cartographer").then((m) =>
            m.cartographer(),
          ),
        ]
      : []),
  ],
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "client", "src"),
      "@assets": path.resolve(import.meta.dirname, "attached_assets"),
    },
  },
  root: path.resolve(import.meta.dirname, "client"),
  build: {
    outDir: path.resolve(import.meta.dirname, "dist/public"),
    emptyOutDir: true,
  },
    publicDir: path.resolve(import.meta.dirname, "client", "public"),
  server: {
  // listen on all addresses so other devices on the network can reach the dev server
  host: "0.0.0.0",
    fs: {
      strict: true,
      deny: ["**/.*"],
    },
  },
});
