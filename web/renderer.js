import {vertexShader,flagShader,quadShader,asciiShader} from './shaders.js';
export class FlagRenderer {
 constructor(canvas,options,onError){
  this.canvas=canvas;this.options=options;this.onError=onError;this.active=true;this.dirty=true;this.yaw=.24;this.pitch=.12;this.zoom=1;this.angle=0;this.time=0;this.last=0;this.budget=1;this.aspect=1.5;this.generation=0;this.points=new Float32Array(40*24*6*5);this.matrix=new Float32Array(16);this.w=1;this.h=1;this.fw=0;this.fh=0;
  const g=this.gl=canvas.getContext('webgl2',{alpha:false,antialias:false,powerPreference:'low-power'});
  if(!g)return new SoftwareRenderer(canvas,options,onError);
  try {this.initialize();this.gestures();new ResizeObserver(()=>{this.dirty=true;}).observe(canvas);canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();this.lost=true;onError('Graphics paused. Waiting for the browser to restore the canvas.');});canvas.addEventListener('webglcontextrestored',()=>{this.lost=false;this.initialize();if(this.image)this.upload(this.image);onError('');});this.loop=this.loop.bind(this);requestAnimationFrame(this.loop);}catch(e){onError(e.message);}
 }
 initialize(){
  const g=this.gl;this.flag=this.program(vertexShader,flagShader);this.post=this.program(quadShader,asciiShader);this.flagTex=this.texture();this.sceneTex=this.texture();this.glyphTex=this.texture();this.fbo=g.createFramebuffer();this.depth=g.createRenderbuffer();this.fw=this.fh=0;
  this.buffer=g.createBuffer();this.quad=g.createBuffer();g.bindBuffer(g.ARRAY_BUFFER,this.quad);g.bufferData(g.ARRAY_BUFFER,new Float32Array([-1,-1,0,0,1,-1,1,0,-1,1,0,1,1,-1,1,0,1,1,1,1,-1,1,0,1]),g.STATIC_DRAW);
  const atlas=document.createElement('canvas');atlas.width=384;atlas.height=32;const ctx=atlas.getContext('2d');ctx.fillStyle='white';ctx.font='27px monospace';ctx.textAlign='center';[...' .,:;irsXAHM#B&@'].forEach((c,i)=>ctx.fillText(c,i*24+12,25));
  g.bindTexture(g.TEXTURE_2D,this.glyphTex);g.texImage2D(g.TEXTURE_2D,0,g.RGBA,g.RGBA,g.UNSIGNED_BYTE,atlas);
  g.bindTexture(g.TEXTURE_2D,this.flagTex);g.texImage2D(g.TEXTURE_2D,0,g.RGBA,1,1,0,g.RGBA,g.UNSIGNED_BYTE,new Uint8Array([0,0,0,0]));this.dirty=true;
 }
 texture(){const g=this.gl,t=g.createTexture();g.bindTexture(g.TEXTURE_2D,t);for(const p of [g.TEXTURE_MIN_FILTER,g.TEXTURE_MAG_FILTER])g.texParameteri(g.TEXTURE_2D,p,g.LINEAR);for(const p of [g.TEXTURE_WRAP_S,g.TEXTURE_WRAP_T])g.texParameteri(g.TEXTURE_2D,p,g.CLAMP_TO_EDGE);return t;}
 program(v,f){const g=this.gl;const compile=(type,source)=>{const s=g.createShader(type);g.shaderSource(s,source);g.compileShader(s);if(!g.getShaderParameter(s,g.COMPILE_STATUS))throw Error(g.getShaderInfoLog(s));return s;};const vs=compile(g.VERTEX_SHADER,v),fs=compile(g.FRAGMENT_SHADER,f),p=g.createProgram();g.attachShader(p,vs);g.attachShader(p,fs);g.linkProgram(p);if(!g.getProgramParameter(p,g.LINK_STATUS))throw Error(g.getProgramInfoLog(p));g.deleteShader(vs);g.deleteShader(fs);return p;}
 setOptions(options){this.options=options;this.dirty=true;}
 async load(url){const generation=++this.generation;const image=new Image();image.src=url;try{await image.decode();if(generation!==this.generation)return;this.image=image;this.aspect=image.naturalWidth/image.naturalHeight;this.upload(image);}catch(e){if(generation===this.generation)this.onError('Could not load this flag image.');}}
 upload(image){if(!this.gl||this.lost)return;const g=this.gl;g.activeTexture(g.TEXTURE0);g.bindTexture(g.TEXTURE_2D,this.flagTex);g.texImage2D(g.TEXTURE_2D,0,g.RGBA,g.RGBA,g.UNSIGNED_BYTE,image);this.dirty=true;this.onError('');}
 reset(){this.yaw=.24;this.pitch=.12;this.zoom=1;this.angle=0;this.dirty=true;}
 gestures(){const c=this.canvas,pointers=new Map();let distance=0,lastTap=0,moved=false;
  c.addEventListener('pointerdown',e=>{c.focus({preventScroll:true});c.setPointerCapture(e.pointerId);pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});moved=false;if(pointers.size===2){const [a,b]=[...pointers.values()];distance=Math.hypot(a.x-b.x,a.y-b.y);}});
  c.addEventListener('pointermove',e=>{if(!pointers.has(e.pointerId))return;const old=pointers.get(e.pointerId);pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});if(pointers.size===1){const dx=e.clientX-old.x,dy=e.clientY-old.y;this.yaw+=dx*.008;this.pitch=Math.max(-1,Math.min(1,this.pitch+dy*.005));if(Math.abs(dx)+Math.abs(dy)>2)moved=true;}else{const [a,b]=[...pointers.values()],d=Math.hypot(a.x-b.x,a.y-b.y);if(distance>0)this.zoom=Math.max(.55,Math.min(1.8,this.zoom*d/distance));distance=d;moved=true;}this.dirty=true;});
  const finish=e=>{pointers.delete(e.pointerId);if(e.type==='pointerup'&&!moved&&pointers.size===0){const now=performance.now();if(now-lastTap<300)this.reset();lastTap=now;}distance=0;};c.addEventListener('pointerup',finish);c.addEventListener('pointercancel',finish);c.addEventListener('lostpointercapture',e=>pointers.delete(e.pointerId));
  c.addEventListener('wheel',e=>{e.preventDefault();this.zoom=Math.max(.55,Math.min(1.8,this.zoom*Math.exp(-e.deltaY*.001)));this.dirty=true;},{passive:false});c.addEventListener('dblclick',()=>this.reset());
 }
 fill(t,wind,aspect){let i=0;const dx=[0,1,0,1,1,0],dy=[0,0,1,0,1,1];for(let y=0;y<24;y++)for(let x=0;x<40;x++)for(let k=0;k<6;k++){const u=(x+dx[k])/40,v=(y+dy[k])/24,phase=10*u-t*3.3+2.2*v;this.points[i++]=(u-wind*.025*u*Math.cos(phase)-.5)*aspect;this.points[i++]=.5-v+wind*u*(.08*Math.sin(8*u-t*2.5+3*v)-.055*u);this.points[i++]=wind*u*(.29*Math.sin(phase)+.1*Math.sin(17*u-t*5.1-5*v));this.points[i++]=u;this.points[i++]=v;}}
 target(w,h){if(w===this.fw&&h===this.fh)return;const g=this.gl;this.fw=w;this.fh=h;g.bindTexture(g.TEXTURE_2D,this.sceneTex);g.texImage2D(g.TEXTURE_2D,0,g.RGBA,w,h,0,g.RGBA,g.UNSIGNED_BYTE,null);g.bindRenderbuffer(g.RENDERBUFFER,this.depth);g.renderbufferStorage(g.RENDERBUFFER,g.DEPTH_COMPONENT16,w,h);g.bindFramebuffer(g.FRAMEBUFFER,this.fbo);g.framebufferTexture2D(g.FRAMEBUFFER,g.COLOR_ATTACHMENT0,g.TEXTURE_2D,this.sceneTex,0);g.framebufferRenderbuffer(g.FRAMEBUFFER,g.DEPTH_ATTACHMENT,g.RENDERBUFFER,this.depth);if(g.checkFramebufferStatus(g.FRAMEBUFFER)!==g.FRAMEBUFFER_COMPLETE)throw Error('The browser could not allocate the flag canvas.');}
 loop(now){requestAnimationFrame(this.loop);if(this.lost)return;const o=this.options,rate=o.lowPower?Math.min(24,o.fps):o.fps;if(!this.active||document.hidden){this.last=now;return;}if(now-this.last<1000/rate)return;if(o.paused&&!this.dirty){this.last=now;return;}const start=performance.now(),dt=this.last?Math.min(.1,(now-this.last)/1000):0;this.last=now;if(!o.paused){this.time+=dt;if(o.orbit)this.angle=(this.angle+o.speed*dt)%360;}try{this.draw(o);this.dirty=false;const elapsed=performance.now()-start;if(o.quality==='auto'&&elapsed>1000/rate&&this.budget>.5)this.budget=Math.max(.5,this.budget-.1);}catch(e){this.onError(e.message);this.active=false;}}
 draw(o){const g=this.gl,rect=this.canvas.getBoundingClientRect(),dpr=Math.min(1.5,devicePixelRatio||1),sizeScale=Math.min(1,2048/Math.max(rect.width*dpr,rect.height*dpr));const w=Math.max(1,Math.round(rect.width*dpr*sizeScale)),h=Math.max(1,Math.round(rect.height*dpr*sizeScale));if(this.canvas.width!==w||this.canvas.height!==h){this.canvas.width=w;this.canvas.height=h;}
  const maxPixels=o.lowPower||o.quality==='low'?420:o.quality==='high'?1280:850;if(o.quality!=='auto')this.budget=1;const scale=Math.min(1,maxPixels*this.budget/Math.max(w,h));this.target(Math.max(1,Math.floor(w*scale)),Math.max(1,Math.floor(h*scale)));
  g.bindFramebuffer(g.FRAMEBUFFER,this.fbo);g.viewport(0,0,this.fw,this.fh);g.enable(g.DEPTH_TEST);g.disable(g.CULL_FACE);g.clearColor(0,0,0,0);g.clear(g.COLOR_BUFFER_BIT|g.DEPTH_BUFFER_BIT);
  const aspect=o.vertical?1/this.aspect:this.aspect;this.fill(this.time,o.wind,aspect);g.useProgram(this.flag);
  const a=this.yaw+this.angle*Math.PI/180,cy=Math.cos(a),sy=Math.sin(a),cp=Math.cos(this.pitch),sp=Math.sin(this.pitch),fit=Math.min(1.65/aspect,1.55*h/w)*this.zoom,ys=fit*w/h;
  this.matrix.set([fit*cy,ys*sp*sy,-cp*sy,0,0,ys*cp,sp,0,fit*sy,-ys*sp*cy,cp*cy,0,0,0,0,1]);
  g.uniformMatrix4fv(g.getUniformLocation(this.flag,'m'),false,this.matrix);g.uniform1i(g.getUniformLocation(this.flag,'vertical'),o.vertical?1:0);
  g.activeTexture(g.TEXTURE0);g.bindTexture(g.TEXTURE_2D,this.flagTex);g.uniform1i(g.getUniformLocation(this.flag,'image'),0);g.bindBuffer(g.ARRAY_BUFFER,this.buffer);g.bufferData(g.ARRAY_BUFFER,this.points,g.DYNAMIC_DRAW);g.enableVertexAttribArray(0);g.enableVertexAttribArray(1);g.vertexAttribPointer(0,3,g.FLOAT,false,20,0);g.vertexAttribPointer(1,2,g.FLOAT,false,20,12);g.drawArrays(g.TRIANGLES,0,40*24*6);
  g.bindFramebuffer(g.FRAMEBUFFER,null);g.viewport(0,0,w,h);g.disable(g.DEPTH_TEST);g.useProgram(this.post);g.activeTexture(g.TEXTURE0);g.bindTexture(g.TEXTURE_2D,this.sceneTex);g.uniform1i(g.getUniformLocation(this.post,'scene'),0);g.activeTexture(g.TEXTURE1);g.bindTexture(g.TEXTURE_2D,this.glyphTex);g.uniform1i(g.getUniformLocation(this.post,'glyphs'),1);
  const columns=Math.max(35,Math.min(o.lowPower?100:180,o.cells));g.uniform2f(g.getUniformLocation(this.post,'grid'),columns,Math.max(12,columns*h/w*.52));for(const [name,value]of Object.entries({ascii:o.ascii,mono:o.monochrome,blocks:o.blocks,liftDark:o.liftDark,sextants:o.sextants}))g.uniform1i(g.getUniformLocation(this.post,name),value?1:0);g.bindBuffer(g.ARRAY_BUFFER,this.quad);g.vertexAttribPointer(0,2,g.FLOAT,false,16,0);g.vertexAttribPointer(1,2,g.FLOAT,false,16,8);g.drawArrays(g.TRIANGLES,0,6);
 }
}

// Match the shared shader's dark-colour lift (RGB values in the 0–255 range).
export function visibleInk(red,green,blue,liftDark){
 const luminance=(red*.2126+green*.7152+blue*.0722)/255;
 const lift=liftDark?Math.max(0,.28-luminance)*255:0;
 return [red,green,blue].map(c=>Math.min(255,c+lift));
}

// Compatibility path for browsers that disable WebGL (bounded CPU canvas).
export class SoftwareRenderer {
 constructor(canvas,options,onError){
  Object.assign(this,{canvas,options,onError,active:true,dirty:true,yaw:.24,pitch:.12,zoom:1,angle:0,time:0,last:0,aspect:1.5,generation:0});
  this.ctx=canvas.getContext('2d',{alpha:false});if(!this.ctx){onError('This browser cannot create a graphics canvas.');return;}
  FlagRenderer.prototype.gestures.call(this);new ResizeObserver(()=>this.dirty=true).observe(canvas);this.loop=this.loop.bind(this);requestAnimationFrame(this.loop);
 }
 setOptions(o){this.options=o;this.dirty=true;}
 reset(){FlagRenderer.prototype.reset.call(this);}
 async load(url){const generation=++this.generation,image=new Image();image.src=url;try{await image.decode();if(generation!==this.generation)return;const off=document.createElement('canvas'),scale=Math.min(1,640/Math.max(image.naturalWidth,image.naturalHeight));off.width=Math.max(1,Math.round(image.naturalWidth*scale));off.height=Math.max(1,Math.round(image.naturalHeight*scale));const c=off.getContext('2d');c.drawImage(image,0,0,off.width,off.height);this.tex=c.getImageData(0,0,off.width,off.height);this.aspect=off.width/off.height;this.dirty=true;this.onError('');}catch(e){this.onError('Could not load this flag image.');}}
 loop(now){requestAnimationFrame(this.loop);if(!this.active||document.hidden){this.last=now;return;}const o=this.options,rate=Math.min(o.lowPower?10:15,o.fps);if(now-this.last<1000/rate)return;if(o.paused&&!this.dirty){this.last=now;return;}const dt=this.last?Math.min(.1,(now-this.last)/1000):0;this.last=now;if(!o.paused){this.time+=dt;if(o.orbit)this.angle=(this.angle+o.speed*dt)%360;}this.draw();this.dirty=false;}
 draw(){const c=this.canvas,ctx=this.ctx,o=this.options,rect=c.getBoundingClientRect();const w=Math.max(1,Math.round(rect.width)),h=Math.max(1,Math.round(rect.height));if(c.width!==w||c.height!==h){c.width=w;c.height=h;}ctx.fillStyle='#090e11';ctx.fillRect(0,0,w,h);if(!this.tex)return;
  const baseCols=Math.min(o.lowPower?65:100,Math.round(o.cells)),baseRows=Math.max(12,Math.round(baseCols*h/w*.52));
  const sextants=o.ascii&&o.sextants,cols=baseCols*(sextants?2:1),rows=baseRows*(sextants?3:1),size=cols*rows;
  if(this.size!==size){this.depth=new Float32Array(size);this.colors=new Uint8Array(size*3);this.shade=new Float32Array(size);this.size=size;}this.depth.fill(-Infinity);
  const tex=this.tex,aspect=o.vertical?1/this.aspect:this.aspect,fit=Math.min(1.65/aspect,1.55*h/w)*this.zoom,a=this.yaw+this.angle*Math.PI/180,cy=Math.cos(a),sy=Math.sin(a),cp=Math.cos(this.pitch),sp=Math.sin(this.pitch),nu=Math.max(100,cols*3),nv=Math.max(60,rows*3);
  for(let j=0;j<nv;j++)for(let i=0;i<nu;i++){
   const u=i/(nu-1),v=j/(nv-1),phase=10*u-this.time*3.3+2.2*v;
   const x=(u-o.wind*.025*u*Math.cos(phase)-.5)*aspect,y=.5-v+o.wind*u*(.08*Math.sin(8*u-this.time*2.5+3*v)-.055*u),z=o.wind*u*(.29*Math.sin(phase)+.1*Math.sin(17*u-this.time*5.1-5*v));
   const xx=x*cy+z*sy,zz=-x*sy+z*cy,yy=y*cp-zz*sp,depth=y*sp+zz*cp,perspective=1/(1-depth*.15),sx=Math.round(cols*(.5+fit*xx*perspective*.5)),sY=Math.round(rows*(.5-fit*w/h*yy*perspective*.5));if(sx<0||sx>=cols||sY<0||sY>=rows)continue;
   const p=sY*cols+sx;if(depth<this.depth[p])continue;const tx=Math.max(0,Math.min(tex.width-1,Math.floor((o.vertical?v:u)*(tex.width-1)))),ty=Math.max(0,Math.min(tex.height-1,Math.floor((o.vertical?1-u:v)*(tex.height-1)))),src=(ty*tex.width+tx)*4;if(tex.data[src+3]<100)continue;
   this.depth[p]=depth;const light=.6+.4*Math.abs(Math.cos(phase));for(let k=0;k<3;k++)this.colors[p*3+k]=tex.data[src+k]*light;this.shade[p]=light;
  }
  const cw=w/cols,ch=h/rows,ramp=' .,:;irsXAHM#B&@';ctx.font=`${Math.ceil(ch*1.05)}px monospace`;ctx.textAlign='center';
  for(let p=0;p<size;p++){if(this.depth[p]===-Infinity)continue;const red=this.colors[p*3],green=this.colors[p*3+1],blue=this.colors[p*3+2],lum=(red*.2126+green*.7152+blue*.0722)/255;const ink=visibleInk(red,green,blue,o.liftDark);ctx.fillStyle=o.monochrome?`rgb(${90+lum*165} ${90+lum*165} ${90+lum*165})`:`rgb(${ink[0]} ${ink[1]} ${ink[2]})`;const x=p%cols*cw,y=Math.floor(p/cols)*ch;if(o.ascii&&!sextants)ctx.fillText(o.blocks?'#':ramp[Math.min(15,Math.floor((.4+lum*.59)*16))],x+cw/2,y+ch*.8);else ctx.fillRect(x,y,cw+1,ch+1);}
 }
}
