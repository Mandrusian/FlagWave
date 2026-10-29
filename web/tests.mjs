import assert from 'node:assert/strict';
import fs from 'node:fs';
import {FlagRenderer,SoftwareRenderer,visibleInk} from './dist/renderer.js';
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

// Dark colours remain distinct from the canvas; bright colours are unchanged.
assert.deepEqual(visibleInk(0,0,0,false),[0,0,0]);
assert(visibleInk(0,0,0,true).every(c=>c>=71&&c<72));
assert.deepEqual(visibleInk(255,255,255,true),[255,255,255]);
assert.deepEqual(visibleInk(255,80,20,true),[255,80,20]);
function renderSample(sextants,alpha=255,liftDark=true,ascii=true){
 const calls=[],ctx={fillRect(...args){calls.push({kind:'block',ink:this.fillStyle,args});},fillText(...args){calls.push({kind:'text',ink:this.fillStyle,args});}};
 const state={canvas:{width:100,height:100,getBoundingClientRect:()=>({width:100,height:100})},ctx,options:{cells:35,ascii,sextants,liftDark,wind:0},tex:{width:1,height:1,data:new Uint8Array([0,0,0,alpha])},aspect:1.5,zoom:1,yaw:0,pitch:0,angle:0,time:0};
 SoftwareRenderer.prototype.draw.call(state);return {calls,state};
}
const shaded=renderSample(false),sextant=renderSample(true);
assert(shaded.calls.some(c=>c.kind==='text'&&c.ink.startsWith('rgb(71.')));
assert(!sextant.calls.some(c=>c.kind==='text'));
assert.equal(sextant.state.size,shaded.state.size*6);
assert.equal(renderSample(true,0).calls.length,1); // Only the background, no opaque rectangle.
assert(renderSample(false,255,false).calls.some(c=>c.ink==='rgb(0 0 0)'));
assert(!renderSample(true,255,true,false).calls.some(c=>c.kind==='text'));
console.log('Dark-colour contrast, sextant subcells, transparency and textured rendering passed.');
