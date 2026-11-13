const sharp=require('sharp');
const P={onko:'<path d="M20 6c-4 0-6 3-6 6 0 5 6 12 6 12s6-7 6-12c0-3-2-6-6-6z"/><path d="M15 21l-6 13 5-1 3 4 5-11M25 21l6 13-5-1-3 4-5-11"/>',
neuro:'<path d="M20 8c-3-3-9-2-10 3-4 1-5 7-1 9-1 5 4 9 8 7 1 2 2 3 3 3V8z"/><path d="M20 8c3-3 9-2 10 3 4 1 5 7 1 9 1 5-4 9-8 7-1 2-2 3-3 3"/>',
srdce:'<path d="M20 33S6 24 6 15c0-5 4-8 8-8 3 0 5 2 6 4 1-2 3-4 6-4 4 0 8 3 8 8 0 9-14 18-14 18z"/><path d="M9 19h7l2-4 3 8 2-4h8"/>',
transpl:'<path d="M16 7c-6 0-9 6-9 13s3 13 9 13c4 0 5-4 3-8-1-3 1-4 1-5s-2-2-1-5c2-4 1-8-3-8z"/><path d="M27 12v16M19 20h16"/>',
nemoc:'<path d="M6 34V14l14-7 14 7v20z"/><path d="M20 15v10M15 20h10M16 34v-5h8v5"/>'};
(async()=>{for(const [k,p] of Object.entries(P)){const svg=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="256" height="256"><circle cx="32" cy="32" r="32" fill="#FCFDFE"/><g transform="translate(12 12)" fill="none" stroke="#1C7FC4" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round">${p}</g></svg>`;await sharp(Buffer.from(svg)).png().toFile(`img/ic_${k}.png`);}})();
