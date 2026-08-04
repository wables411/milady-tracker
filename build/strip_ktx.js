// Rewrite a GLB: replace KTX2 images with 1x1 PNG placeholders and drop
// KHR_texture_basisu so Blender's importer accepts it (geometry/rig intact).
const fs = require('fs');

const [,, inPath, outPath] = process.argv;
const buf = fs.readFileSync(inPath);
const jsonLen = buf.readUInt32LE(12);
const json = JSON.parse(buf.slice(20, 20 + jsonLen).toString('utf8'));
const binStart = 20 + jsonLen + 8;
const bin = buf.slice(binStart, binStart + buf.readUInt32LE(20 + jsonLen));

// 1x1 white PNG
const PNG1 = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
  'base64');

const pad4 = n => (n + 3) & ~3;
let newBin = Buffer.concat([bin, Buffer.alloc(pad4(bin.length) - bin.length)]);
const pngOffset = newBin.length;
newBin = Buffer.concat([newBin, PNG1, Buffer.alloc(pad4(PNG1.length) - PNG1.length)]);

json.bufferViews = json.bufferViews || [];
const pngBV = json.bufferViews.length;
json.bufferViews.push({ buffer: 0, byteOffset: pngOffset, byteLength: PNG1.length });

let replaced = 0;
for (const img of json.images || []) {
  if (img.mimeType === 'image/ktx2') {
    img.mimeType = 'image/png';
    img.bufferView = pngBV;
    delete img.uri;
    replaced++;
  }
}
for (const tex of json.textures || []) {
  const b = tex.extensions?.KHR_texture_basisu;
  if (b) {
    tex.source = b.source;
    delete tex.extensions.KHR_texture_basisu;
    if (!Object.keys(tex.extensions).length) delete tex.extensions;
  }
}
for (const k of ['extensionsUsed', 'extensionsRequired']) {
  if (json[k]) {
    json[k] = json[k].filter(e => e !== 'KHR_texture_basisu');
    if (!json[k].length) delete json[k];
  }
}
json.buffers[0].byteLength = newBin.length;

let jsonBuf = Buffer.from(JSON.stringify(json), 'utf8');
jsonBuf = Buffer.concat([jsonBuf, Buffer.alloc(pad4(jsonBuf.length) - jsonBuf.length, 0x20)]);

const header = Buffer.alloc(12);
header.write('glTF', 0);
header.writeUInt32LE(2, 4);
header.writeUInt32LE(12 + 8 + jsonBuf.length + 8 + newBin.length, 8);
const jsonHdr = Buffer.alloc(8);
jsonHdr.writeUInt32LE(jsonBuf.length, 0);
jsonHdr.writeUInt32LE(0x4E4F534A, 4); // 'JSON'
const binHdr = Buffer.alloc(8);
binHdr.writeUInt32LE(newBin.length, 0);
binHdr.writeUInt32LE(0x004E4942, 4); // 'BIN'
fs.writeFileSync(outPath, Buffer.concat([header, jsonHdr, jsonBuf, binHdr, newBin]));
console.log(`replaced ${replaced} ktx2 images; wrote ${outPath}`);
