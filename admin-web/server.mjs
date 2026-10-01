import { createReadStream, existsSync, statSync } from 'node:fs';
import { createServer } from 'node:http';
import { extname, join, normalize } from 'node:path';
import { applySecurityHeaders } from './security-headers.mjs';

const root = join(process.cwd(), 'dist');
const port = Number.parseInt(process.env.PORT || '4173', 10);
const mimeTypes = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.webmanifest': 'application/manifest+json',
};

export function resolveRequestPath(rawUrl) {
  // A malformed escape (e.g. "/%E0%A4%A") throws; never let it crash the server.
  try {
    return decodeURIComponent(new URL(rawUrl || '/', 'http://localhost').pathname);
  } catch {
    return null;
  }
}

const server = createServer((request, response) => {
  applySecurityHeaders(response);
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    response.statusCode = 405;
    response.setHeader('Allow', 'GET, HEAD');
    response.end();
    return;
  }
  const pathname = resolveRequestPath(request.url);
  if (pathname === null || pathname.includes('\0')) {
    response.statusCode = 400;
    response.end('Bad request');
    return;
  }
  const relativePath = normalize(pathname).replace(/^(\.\.[/\\])+/, '').replace(/^[/\\]+/, '');
  let filePath = join(root, relativePath);

  if (!existsSync(filePath) || !statSync(filePath).isFile()) {
    filePath = join(root, 'index.html');
  }

  response.setHeader('Content-Type', mimeTypes[extname(filePath)] || 'application/octet-stream');
  response.setHeader(
    'Cache-Control',
    filePath.includes(`${join(root, 'assets')}`) ? 'public, max-age=31536000, immutable' : 'no-cache',
  );
  const stream = createReadStream(filePath);
  stream.on('error', () => {
    if (!response.headersSent) response.statusCode = 500;
    response.end();
  });
  stream.pipe(response);
});

server.on('clientError', (_error, socket) => {
  if (socket.writable) socket.end('HTTP/1.1 400 Bad Request\r\n\r\n');
});

if (process.env.NODE_ENV !== 'test' && !process.env.VITEST) {
  server.listen(port, '0.0.0.0', () => {
    console.log(`AgrowAI Admin Web listening on port ${port}`);
  });
}

export { server };
