// [cc] Collection server — serves gallery page + individual card viewers from projects/
import http from 'node:http';
import { readFile, stat, readdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = __dirname;
const projectsDir = path.resolve(__dirname, '..', 'projects');
const port = Number(process.env.PORT || 4173);

const types = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.glb': 'model/gltf-binary',
  '.mp4': 'video/mp4',
};

// [cc] Scan projects/ for card-config.json files and return metadata for gallery
async function getCards() {
  const cards = [];
  let entries;
  try {
    entries = await readdir(projectsDir, { withFileTypes: true });
  } catch {
    return cards;
  }
  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    const configPath = path.join(projectsDir, entry.name, 'card-config.json');
    try {
      const raw = await readFile(configPath, 'utf-8');
      const config = JSON.parse(raw);
      // [cc] Check if web/ dir exists (card has been built)
      const webDir = path.join(projectsDir, entry.name, 'web');
      let hasWeb = false;
      try {
        hasWeb = (await stat(webDir)).isDirectory();
      } catch {}
      cards.push({
        slug: entry.name,
        title: config.title,
        subtitle: config.subtitle,
        technique: config.technique,
        tagline: config.tagline,
        edition: config.edition,
        collection: config.collection,
        description: config.description,
        hasWeb,
        // [cc] Thumbnail path — use subject.png from assets
        thumbnail: `/card/${entry.name}/assets/subject.png`,
        background: `/card/${entry.name}/assets/background.png`,
      });
    } catch {
      // [cc] Skip projects without valid config
    }
  }
  return cards;
}

// [cc] Serve a file with security checks
async function serveFile(filePath, res) {
  try {
    const data = await readFile(filePath);
    const ext = path.extname(filePath);
    res.writeHead(200, {
      'Content-Type': types[ext] || 'application/octet-stream',
      'Cache-Control': 'no-cache',
    });
    res.end(data);
  } catch {
    res.writeHead(404);
    res.end('Not found');
  }
}

http.createServer(async (req, res) => {
  const url = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);

  // [cc] API endpoint — returns all card metadata as JSON
  if (url === '/api/cards') {
    const cards = await getCards();
    res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
    return res.end(JSON.stringify(cards));
  }

  // [cc] Card viewer — serve files from projects/<slug>/web/
  const cardMatch = url.match(/^\/card\/([^/]+)(\/.*)?$/);
  if (cardMatch) {
    const slug = cardMatch[1];
    let subPath = cardMatch[2] || '/index.html';
    if (subPath === '/') subPath = '/index.html';

    const webDir = path.join(projectsDir, slug, 'web');
    const filePath = path.resolve(webDir, '.' + subPath);

    // [cc] Security: ensure resolved path stays within the web dir
    if (!filePath.startsWith(webDir + path.sep) && filePath !== webDir) {
      res.writeHead(403);
      return res.end('Forbidden');
    }

    return serveFile(filePath, res);
  }

  // [cc] Gallery — serve files from collection/ dir
  let filePath = path.resolve(root, '.' + url);
  if (filePath === root || url === '/') {
    filePath = path.join(root, 'index.html');
  }

  // [cc] Security: ensure resolved path stays within collection dir
  if (!filePath.startsWith(root + path.sep) && filePath !== root) {
    res.writeHead(403);
    return res.end('Forbidden');
  }

  return serveFile(filePath, res);
}).listen(port, '0.0.0.0', () => {
  console.log(`Holo Card Studio Collection: http://127.0.0.1:${port}`);
});
