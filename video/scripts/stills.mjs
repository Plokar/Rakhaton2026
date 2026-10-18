// QA: jeden bundle, víc statických snímků. node scripts/stills.mjs <Kompozice> <měřítko> <snímek...>
import { bundle } from '@remotion/bundler';
import { renderStill, selectComposition } from '@remotion/renderer';
import { fileURLToPath } from 'node:url';
const [id, scale, ...frames] = process.argv.slice(2);
const serveUrl = await bundle({ entryPoint: fileURLToPath(new URL('../src/index.ts', import.meta.url)) });
const composition = await selectComposition({ serveUrl, id, inputProps: { bgm: true } });
for (const f of frames) {
  await renderStill({ serveUrl, composition, frame: Number(f), scale: Number(scale), output: fileURLToPath(new URL(`../out/qa/${({ MedTeamHook: 'a', MedTeamWalkthrough: 'w' })[id] ?? id}_${f}.png`, import.meta.url)), inputProps: { bgm: true } });
  process.stdout.write(`${f} `);
}
console.log('hotovo');
