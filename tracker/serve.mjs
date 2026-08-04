// Tiny static server for the avatar tracker — zero dependencies.
// Serves the obs/avatar folder at http://127.0.0.1:8787
import http from 'node:http';
import { readFile } from 'node:fs/promises';
import { extname, join, normalize } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
const mime = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript',
  '.mjs': 'text/javascript',
  '.vrm': 'application/octet-stream',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.json': 'application/json',
  '.md': 'text/plain; charset=utf-8',
};

http.createServer(async (req, res) => {
  try {
    let p = decodeURIComponent(new URL(req.url, 'http://x').pathname);
    if (p === '/') p = '/tracker/index.html';
    const file = normalize(join(root, p));
    if (!file.startsWith(normalize(root))) throw new Error('path escape');
    const data = await readFile(file);
    res.writeHead(200, { 'content-type': mime[extname(file).toLowerCase()] || 'application/octet-stream', 'cache-control': 'no-cache' });
    res.end(data);
  } catch {
    res.writeHead(404);
    res.end('not found');
  }
}).listen(8787, () => console.log('avatar tracker running: http://127.0.0.1:8787'));
