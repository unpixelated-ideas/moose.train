favicon.gg — favicon package
=============================

1. Copy every file in this folder to the root of your site
   (Next.js / Vite / Astro: the "public" folder, so they end up at /).
2. Paste this into the <head> of your HTML:

<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<meta name="theme-color" content="#5b3fe6">

3. Hard-refresh (Cmd/Ctrl + Shift + R). Browsers cache favicons aggressively,
   so an old icon in your tab is usually cache, not a broken file.

Files
-----
favicon.ico                    16 · 32 · 48 — the universal fallback every browser understands
favicon-16x16.png              Browser tab and bookmark bar
favicon-32x32.png              Retina tabs and shortcuts
apple-touch-icon.png           180×180, opaque — iOS home screen
android-chrome-192x192.png     Android home screen
android-chrome-512x512.png     Splash screens and app stores
site.webmanifest               Install metadata for Android and PWA

Generated with https://favicon.gg — processed locally in your browser.
