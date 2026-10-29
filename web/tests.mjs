import assert from 'node:assert/strict';
import fs from 'node:fs';
import {FlagRenderer} from './dist/renderer.js';
import {asciiShader} from './dist/shaders.js';
const count=40*24*6*5,a={points:new Float32Array(count)},b={points:new Float32Array(count)};
FlagRenderer.prototype.fill.call(a,0,1,1.5);FlagRenderer.prototype.fill.call(b,2,1,1.5);
assert(a.points.every(Number.isFinite));assert.notDeepEqual(a.points,b.points);
for(let i=0;i<count;i+=5){const u=a.points[i+3],v=a.points[i+4];assert(u>=0&&u<=1&&v>=0&&v<=1);if(u===0){assert.equal(a.points[i],-.75);assert.equal(a.points[i+2],0);assert.equal(a.points[i],b.points[i]);assert.equal(a.points[i+1],b.points[i+1]);}}
const flags=JSON.parse(fs.readFileSync(new URL('./dist/catalogue.json',import.meta.url)));
assert.equal(flags.length,424);assert.equal(new Set(flags.map(f=>f.id)).size,424);
assert.equal(flags.find(f=>f.id==='red-eureka').name,'Red Eureka');
for(const f of flags)assert(fs.existsSync(new URL('./dist/'+f.asset,import.meta.url)));
assert(asciiShader.includes('uniform bool blocks'));
console.log('Web cloth, pinned hoist, shared shaders and all 424 packaged flags passed.');
