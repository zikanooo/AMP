import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import { Readable } from 'stream';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = 3000;
const HOST = '0.0.0.0';

// Dedicated Third-Party AM & Preset Resolver (Replaces obsolete Open Motion API)
app.all('/api/am/status', (req, res) => {
  res.setHeader('Content-Type', 'application/json');
  res.setHeader('Access-Control-Allow-Origin', '*');
  return res.json({
    version: 'V6.0.0',
    protocol: 2,
    resolver: 'motion-third-party-resolver',
    authentication: 'none',
    mode: 'dual-anonymous',
    providers: ['official', 'zervida', 'third-party'],
    maxPackageBytes: 52428800,
    maxZervidaMediaBytes: 268435456,
    stateless: true
  });
});

app.all('/api/am/project', async (req, res) => {
  res.setHeader('Content-Type', 'application/json');
  res.setHeader('Access-Control-Allow-Origin', '*');
  
  const rawUrl = (req.query.url || req.query.link || req.body?.url || '').trim();
  const provider = (req.query.provider || 'zervida').trim();
  const projectName = (req.query.project || '').trim();

  if (!rawUrl) {
    return res.status(400).json({
      error: 'Masukkan tautan preset Alight Motion atau XML.',
      code: 'MISSING_URL'
    });
  }

  try {
    let target = rawUrl;
    // Normalize Google Drive direct download link
    if (target.includes('drive.google.com')) {
      const match = target.match(/\/d\/([a-zA-Z0-9_-]+)/) || target.match(/id=([a-zA-Z0-9_-]+)/);
      if (match) {
        target = `https://drive.google.com/uc?export=download&id=${match[1]}&confirm=t`;
      }
    } else if (target.includes('dropbox.com')) {
      target = target.replace(/[?&]dl=0/, '?dl=1');
      if (!target.includes('dl=1')) target += (target.includes('?') ? '&dl=1' : '?dl=1');
    }

    const fetchHeaders = {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
      'Accept': 'text/html,application/xhtml+xml,application/xml,application/zip,application/octet-stream;q=0.9,*/*;q=0.8'
    };

    let response;
    try {
      response = await fetch(target, {
        headers: fetchHeaders,
        redirect: 'follow',
        signal: AbortSignal.timeout(20000)
      });
    } catch (netErr) {
      // Fallback via third-party CORS proxy if direct fetch is blocked
      const proxyUrl = `https://api.allorigins.win/raw?url=${encodeURIComponent(target)}`;
      response = await fetch(proxyUrl, {
        headers: fetchHeaders,
        signal: AbortSignal.timeout(20000)
      });
    }

    if (!response.ok) {
      return res.status(response.status).json({
        error: `Gagal mengunduh preset (HTTP ${response.status}). Periksa izin tautan Anda.`,
        code: 'DOWNLOAD_FAILED'
      });
    }

    const contentType = response.headers.get('content-type') || '';
    const bodyText = await response.text();
    const trimmed = bodyText.trim();

    // Check if response is raw XML scene directly
    if (trimmed.startsWith('<?xml') || trimmed.startsWith('<scene') || /<scene\b/i.test(trimmed)) {
      const titleMatch = trimmed.match(/<scene\b[^>]*\btitle="([^"]+)"/i);
      const title = titleMatch ? titleMatch[1] : 'Preset Motion';
      const pkgId = Math.random().toString(16).slice(2).padStart(16, '0') + Math.random().toString(16).slice(2).padStart(16, '0');

      return res.json({
        xml: trimmed,
        xmlName: projectName || 'preset.xml',
        title,
        packageId: pkgId,
        projects: [{ name: projectName || 'preset.xml', title }],
        media: [],
        provider: provider === 'official' ? 'official' : 'zervida',
        resolver: provider === 'official' ? 'open-motion-official-am' : 'open-motion-zervida-adapter',
        shareLink: rawUrl
      });
    }

    // If it's an Alight Creative HTML share page
    if (trimmed.startsWith('<!DOCTYPE') || trimmed.startsWith('<html') || contentType.includes('text/html')) {
      const ogTitleMatch = trimmed.match(/<meta\s+property=["']og:title["']\s+content=["']([^"']+)["']/i) || trimmed.match(/<title>([^<]+)<\/title>/i);
      const ogDescMatch = trimmed.match(/<meta\s+property=["']og:description["']\s+content=["']([^"']+)["']/i);
      const title = ogTitleMatch ? ogTitleMatch[1].replace(/\s*-\s*Alight.*$/i, '').trim() : 'Alight Motion Preset';
      const desc = ogDescMatch ? ogDescMatch[1].trim() : '';

      // Check if XML was embedded in the page
      const xmlEmbeddedMatch = trimmed.match(/<scene\b[\s\S]*?<\/scene>/i);
      if (xmlEmbeddedMatch) {
        const pkgId = Math.random().toString(16).slice(2).padStart(16, '0') + Math.random().toString(16).slice(2).padStart(16, '0');
        return res.json({
          xml: xmlEmbeddedMatch[0],
          xmlName: projectName || 'preset.xml',
          title,
          packageId: pkgId,
          projects: [{ name: projectName || 'preset.xml', title }],
          media: [],
          provider: provider === 'official' ? 'official' : 'zervida',
          resolver: provider === 'official' ? 'open-motion-official-am' : 'open-motion-zervida-adapter',
          shareLink: rawUrl
        });
      }

      return res.status(400).json({
        error: `Preset "${title}" terdeteksi dari Alight Creative. Link share cloud memerlukan file XML langsung atau tempel isi XML ke kotak impor.`,
        title,
        description: desc,
        code: 'AM_CLOUD_LINK_REQUIRES_XML'
      });
    }

    return res.status(400).json({
      error: 'Format data tidak dikenali sebagai XML scene Alight Motion.',
      code: 'UNRECOGNIZED_FORMAT'
    });

  } catch (err) {
    console.error('[AM Resolver Proxy Error]:', err.message);
    return res.status(500).json({
      error: `Kendala pemrosesan preset: ${err.message}`,
      code: 'RESOLVER_ERROR'
    });
  }
});

// Fallback for any other /api/am/* endpoint so it never returns HTML
app.all('/api/am/*', (req, res) => {
  res.setHeader('Content-Type', 'application/json');
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.status(404).json({ error: 'Endpoint resolver tidak ditemukan', code: 'NOT_FOUND' });
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
