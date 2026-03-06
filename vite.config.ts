import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import os from "os";
import runtimeErrorOverlay from "@replit/vite-plugin-runtime-error-modal";
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  plugins: [
    react(),
    runtimeErrorOverlay(),
    VitePWA({
      registerType: 'prompt',
      includeAssets: ['favicon.ico', 'icons/*.png', '*.webp'],
      manifest: {
        name: 'NEET BRO - NEET Test Platform',
        short_name: 'NEET BRO',
        description: 'Comprehensive NEET test preparation platform with AI-powered insights',
        theme_color: '#4f46e5',
        background_color: '#ffffff',
        display: 'standalone',
        orientation: 'portrait-primary',
        scope: '/',
        start_url: '/',
        icons: [
          {
            src: '/icons/icon-72.png',
            sizes: '72x72',
            type: 'image/png',
            purpose: 'any'
          },
          {
            src: '/icons/icon-96.png',
            sizes: '96x96',
            type: 'image/png',
            purpose: 'any'
          },
          {
            src: '/icons/icon-128.png',
            sizes: '128x128',
            type: 'image/png',
            purpose: 'any'
          },
          {
            src: '/icons/icon-144.png',
            sizes: '144x144',
            type: 'image/png',
            purpose: 'any'
          },
          {
            src: '/icons/icon-152.png',
            sizes: '152x152',
            type: 'image/png',
            purpose: 'any'
          },
          {
            src: '/icons/icon-192.png',
            sizes: '192x192',
            type: 'image/png',
            purpose: 'any maskable'
          },
          {
            src: '/icons/icon-384.png',
            sizes: '384x384',
            type: 'image/png',
            purpose: 'any'
          },
          {
            src: '/icons/icon-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any maskable'
          }
        ],
        categories: ['education', 'productivity'],
        shortcuts: [
          {
            name: 'Start Test',
            short_name: 'Test',
            description: 'Start a new practice test',
            url: '/',
            icons: [{ src: '/icons/icon-192.png', sizes: '192x192' }]
          },
          {
            name: 'Dashboard',
            short_name: 'Dashboard',
            description: 'View your performance dashboard',
            url: '/dashboard',
            icons: [{ src: '/icons/icon-192.png', sizes: '192x192' }]
          }
        ]
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,webp,woff,woff2}'],
        runtimeCaching: [
          // Google Fonts caching
          {
            urlPattern: /^https:\/\/fonts\.googleapis\.com\/.*/i,
            handler: 'CacheFirst',
            options: {
              cacheName: 'google-fonts-cache',
              expiration: {
                maxEntries: 10,
                maxAgeSeconds: 60 * 60 * 24 * 365 // 1 year
              },
              cacheableResponse: {
                statuses: [0, 200]
              }
            }
          },
          {
            urlPattern: /^https:\/\/fonts\.gstatic\.com\/.*/i,
            handler: 'CacheFirst',
            options: {
              cacheName: 'gstatic-fonts-cache',
              expiration: {
                maxEntries: 10,
                maxAgeSeconds: 60 * 60 * 24 * 365 // 1 year
              },
              cacheableResponse: {
                statuses: [0, 200]
              }
            }
          },
          // PWA: API caching for safe GET endpoints (read-only data)
          // NetworkFirst: Try network first, fall back to cache if offline
          {
            urlPattern: /\/api\/students\/me\/?$/,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-student-profile',
              expiration: {
                maxEntries: 5,
                maxAgeSeconds: 60 * 60 * 24 // 24 hours
              },
              cacheableResponse: {
                statuses: [200]
              },
              networkTimeoutSeconds: 10, // Fall back to cache if network takes > 10s
            }
          },
          {
            urlPattern: /\/api\/topics\/?.*$/,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-topics',
              expiration: {
                maxEntries: 50,
                maxAgeSeconds: 60 * 60 * 24 * 7 // 7 days
              },
              cacheableResponse: {
                statuses: [200]
              },
              networkTimeoutSeconds: 10,
            }
          },
          {
            urlPattern: /\/api\/subjects\/?.*$/,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-subjects',
              expiration: {
                maxEntries: 30,
                maxAgeSeconds: 60 * 60 * 24 * 7 // 7 days
              },
              cacheableResponse: {
                statuses: [200]
              },
              networkTimeoutSeconds: 10,
            }
          },
          {
            urlPattern: /\/api\/test-sessions\/[^/]+\/?$/,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-test-sessions',
              expiration: {
                maxEntries: 20,
                maxAgeSeconds: 60 * 60 * 24 // 24 hours
              },
              cacheableResponse: {
                statuses: [200]
              },
              networkTimeoutSeconds: 10,
            }
          },
          {
            urlPattern: /\/api\/dashboard\/?.*$/,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-dashboard',
              expiration: {
                maxEntries: 10,
                maxAgeSeconds: 60 * 60 * 24 // 24 hours
              },
              cacheableResponse: {
                statuses: [200]
              },
              networkTimeoutSeconds: 10,
            }
          },
          // Image caching
          {
            urlPattern: /\.(?:png|jpg|jpeg|svg|gif|webp)$/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'images-cache',
              expiration: {
                maxEntries: 50,
                maxAgeSeconds: 60 * 60 * 24 * 30 // 30 days
              }
            }
          },
          // Static resources caching
          {
            urlPattern: /\.(?:js|css)$/,
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'static-resources',
              expiration: {
                maxEntries: 30,
                maxAgeSeconds: 60 * 60 * 24 * 7 // 7 days
              }
            }
          }
        ],
        navigateFallback: '/index.html',
        navigateFallbackDenylist: [/^\/api/, /^\/admin/, /^\/auth/],
        cleanupOutdatedCaches: true,
        skipWaiting: false,
        clientsClaim: true
      },
      devOptions: {
        enabled: false,
        type: 'module',
        navigateFallback: '/index.html'
      }
    }),
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
    rollupOptions: {
      // Ensure service worker is not bundled
      input: {
        main: path.resolve(import.meta.dirname, "client", "index.html"),
      },
    },
  },
    publicDir: path.resolve(import.meta.dirname, "client", "public"),
  server: {
  // listen on all addresses so other devices on the network can reach the dev server
  host: "0.0.0.0",
    // Proxy API requests to Django backend running on localhost:8001
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
        secure: false,
      },
    },
    fs: {
      strict: true,
      deny: ["**/.*"],
    },
  },
});
