import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import { Readable } from 'stream';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3000;
const HOST = process.env.HOST || '0.0.0.0';

// Proxy /api/am/* requests to the upstream Cloudflare AM resolver with valid origin
app.all('/api/am/*', async (req, res) => {
  const upstreamBase = 'https://resolver.openmotionapp.my.id';
  const targetUrl = new URL(req.originalUrl, upstreamBase);

  try {
    const upstreamHeaders = {
      'Origin': 'https://hada45.github.io',
      'Referer': 'https://hada45.github.io/',
      'User-Agent': req.headers['user-agent'] || 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
      'Accept': req.headers['accept'] || '*/*'
    };

    if (req.headers['content-type']) {
      upstreamHeaders['Content-Type'] = req.headers['content-type'];
    }

    const fetchOptions = {
      method: req.method,
      headers: upstreamHeaders,
    };

    if (['POST', 'PUT', 'PATCH'].includes(req.method)) {
      fetchOptions.body = req;
      fetchOptions.duplex = 'half';
    }

    const upstreamResponse = await fetch(targetUrl.href, fetchOptions);

    res.status(upstreamResponse.status);
    upstreamResponse.headers.forEach((val, key) => {
      if (!['content-encoding', 'transfer-encoding', 'connection', 'content-length'].includes(key.toLowerCase())) {
        res.setHeader(key, val);
      }
    });
    res.setHeader('Access-Control-Allow-Origin', '*');

    if (upstreamResponse.body) {
      Readable.fromWeb(upstreamResponse.body).pipe(res);
    } else {
      res.end();
    }
  } catch (err) {
    console.warn('[AM Resolver Proxy Error]:', err.message);
    if (req.path === '/api/am/status') {
      // Fallback status so local editor keeps working
      return res.json({
        version: 'V5.194',
        protocol: 2,
        resolver: 'open-motion-cloudflare-am',
        authentication: 'none',
        mode: 'dual-anonymous',
        providers: ['official', 'zervida'],
        maxPackageBytes: 5242880,
        maxZervidaMediaBytes: 268435456,
        stateless: true
      });
    }
    res.status(502).json({ error: 'Backend resolver error', message: err.message });
  }
});

// Serve static files with proper MIME types and cache headers
app.use(express.static(__dirname, {
  setHeaders: (res, filePath) => {
    if (filePath.endsWith('.webmanifest')) {
      res.setHeader('Content-Type', 'application/manifest+json');
    }
    if (filePath.endsWith('.html') || filePath.endsWith('sw.js')) {
      res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
      res.setHeader('Pragma', 'no-cache');
      res.setHeader('Expires', '0');
    }
  }
}));

// Route fallback for client-side navigation
app.get('*', (req, res) => {
  res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
  res.setHeader('Pragma', 'no-cache');
  res.setHeader('Expires', '0');
  res.sendFile(path.join(__dirname, 'index.html'));
});

app.listen(Number(PORT), HOST, () => {
  console.log(`Open Motion server listening on http://${HOST}:${PORT}`);
});
