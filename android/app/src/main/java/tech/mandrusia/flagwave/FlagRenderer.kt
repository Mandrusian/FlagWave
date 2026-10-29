package tech.mandrusia.flagwave

import android.content.Context
import android.graphics.*
import android.opengl.GLES30.*
import android.opengl.GLSurfaceView
import android.opengl.GLUtils
import android.opengl.Matrix
import android.view.MotionEvent
import android.view.GestureDetector
import android.view.ScaleGestureDetector
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.concurrent.atomic.AtomicReference
import javax.microedition.khronos.egl.EGLConfig
import javax.microedition.khronos.opengles.GL10
import kotlin.math.*

data class RenderOptions(
    val paused: Boolean=false, val orbit: Boolean=true, val speed: Float=6f,
    val wind: Float=1f, val ascii: Boolean=true, val monochrome: Boolean=false,
    val vertical: Boolean=false, val lowPower: Boolean=false, val cells: Float=100f,
    val fps: Int=60, val quality: String="auto", val blocks: Boolean=false,
    val layout: String="auto", val resetToken: Int=0,
    val liftDark: Boolean=true, val sextants: Boolean=false
)
object NativeCloth {
    init { System.loadLibrary("flagwave") }
    external fun fill(buffer: java.nio.FloatBuffer, time: Float, wind: Float, aspect: Float)
}
class FlagSurface(context: Context): GLSurfaceView(context) {
    val engine=FlagRenderer()
    private var lastX=0f; private var lastY=0f
    private val doubleTap=GestureDetector(context,object: GestureDetector.SimpleOnGestureListener() {
        override fun onDown(e:MotionEvent)=true
        override fun onDoubleTap(e:MotionEvent):Boolean {engine.resetRequested=true;return true}
    })
    private val pinch=ScaleGestureDetector(context,object: ScaleGestureDetector.SimpleOnScaleGestureListener() {
        override fun onScale(detector: ScaleGestureDetector):Boolean {
            engine.zoom=(engine.zoom*detector.scaleFactor).coerceIn(.55f,1.8f); return true
        }
    })
    init { setEGLContextClientVersion(3); preserveEGLContextOnPause=true; setRenderer(engine) }
    override fun onTouchEvent(event: MotionEvent):Boolean {
        doubleTap.onTouchEvent(event)
        pinch.onTouchEvent(event)
        when(event.actionMasked) {
            MotionEvent.ACTION_DOWN -> { lastX=event.x; lastY=event.y; parent?.requestDisallowInterceptTouchEvent(true) }
            MotionEvent.ACTION_MOVE -> {
                if(event.pointerCount==1 && !pinch.isInProgress) {
                    engine.dragYaw+=(event.x-lastX)*.008f
                    engine.pitch=(engine.pitch+(event.y-lastY)*.005f).coerceIn(-1f,1f)
                }
                lastX=event.x; lastY=event.y
            }
            MotionEvent.ACTION_UP -> { performClick(); parent?.requestDisallowInterceptTouchEvent(false) }
            MotionEvent.ACTION_CANCEL -> parent?.requestDisallowInterceptTouchEvent(false)
        }
        return true
    }
    override fun performClick():Boolean { super.performClick(); return true }
}
class FlagRenderer: GLSurfaceView.Renderer {
    val options=AtomicReference(RenderOptions())
    val pending=AtomicReference<Bitmap?>(null)
    @Volatile var dragYaw=.24f
    @Volatile var pitch=.12f
    @Volatile var zoom=1f
    @Volatile var failure:String?=null
    @Volatile var resetRequested=false
    private var resetToken=0
    private val vertices=ByteBuffer.allocateDirect(40*24*6*5*4).order(ByteOrder.nativeOrder()).asFloatBuffer()
    private val quad=ByteBuffer.allocateDirect(6*4*4).order(ByteOrder.nativeOrder()).asFloatBuffer().apply {
        put(floatArrayOf(-1f,-1f,0f,0f,1f,-1f,1f,0f,-1f,1f,0f,1f,1f,-1f,1f,0f,1f,1f,1f,1f,-1f,1f,0f,1f));position(0)
    }
    private val matrix=FloatArray(16)
    private var flagProgram=0; private var postProgram=0
    private var flagTexture=0; private var glyphTexture=0; private var sceneTexture=0; private var fbo=0; private var depth=0
    private var w=1;private var h=1;private var fw=1;private var fh=1
    private var imageAspect=1.5f; private var time=0f;private var orbitAngle=0f
    private var previous=0L; private var retained:Bitmap?=null; private var budget=1f
    override fun onSurfaceCreated(gl:GL10?,config:EGLConfig?) {
        try {
            flagProgram=program(vertexShader,flagShader);postProgram=program(quadShader,asciiShader)
            flagTexture=texture(); glyphTexture=texture(); sceneTexture=texture()
            val ids=IntArray(1);glGenFramebuffers(1,ids,0);fbo=ids[0];glGenRenderbuffers(1,ids,0);depth=ids[0]
            val atlas=Bitmap.createBitmap(16*24,32,Bitmap.Config.ARGB_8888)
            val canvas=Canvas(atlas);val paint=Paint(Paint.ANTI_ALIAS_FLAG).apply { color=Color.WHITE;typeface=Typeface.MONOSPACE;textSize=27f;textAlign=Paint.Align.CENTER }
            val ramp=" .,:;irsXAHM#B&@"
            for(i in ramp.indices) canvas.drawText(ramp[i].toString(),i*24f+12,25f,paint)
            glBindTexture(GL_TEXTURE_2D,glyphTexture);GLUtils.texImage2D(GL_TEXTURE_2D,0,atlas,0);atlas.recycle()
            glBindTexture(GL_TEXTURE_2D,flagTexture)
            val image=retained?:Bitmap.createBitmap(1,1,Bitmap.Config.ARGB_8888).apply {eraseColor(Color.TRANSPARENT)}
            GLUtils.texImage2D(GL_TEXTURE_2D,0,image,0)
            previous=0; fw=0;fh=0
        } catch(e:Exception) {failure=e.message?:"Renderer unavailable"}
    }
    override fun onSurfaceChanged(gl:GL10?,width:Int,height:Int) { w=max(1,width);h=max(1,height);previous=0 }
    private fun target(width:Int,height:Int) {
        if(fw==width && fh==height) return
        fw=width;fh=height
        glBindTexture(GL_TEXTURE_2D,sceneTexture)
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,fw,fh,0,GL_RGBA,GL_UNSIGNED_BYTE,null)
        glBindRenderbuffer(GL_RENDERBUFFER,depth);glRenderbufferStorage(GL_RENDERBUFFER,GL_DEPTH_COMPONENT16,fw,fh)
        glBindFramebuffer(GL_FRAMEBUFFER,fbo)
        glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,sceneTexture,0)
        glFramebufferRenderbuffer(GL_FRAMEBUFFER,GL_DEPTH_ATTACHMENT,GL_RENDERBUFFER,depth)
        check(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE) {"Incomplete render target"}
    }
    override fun onDrawFrame(gl:GL10?) {
        if(failure!=null) {glClearColor(.05f,.08f,.1f,1f);glClear(GL_COLOR_BUFFER_BIT);return}
        val start=System.nanoTime();val s=options.get()
        if(resetRequested || s.resetToken!=resetToken) {
            dragYaw=.24f;pitch=.12f;zoom=1f;orbitAngle=0f;resetRequested=false;resetToken=s.resetToken
        }
        val dt=if(previous==0L) 0f else ((start-previous)/1e9).toFloat().coerceIn(0f,.1f);previous=start
        if(!s.paused) { time+=dt; if(s.orbit) orbitAngle=(orbitAngle+s.speed*dt)%360f }
        pending.getAndSet(null)?.let { image ->
            retained?.recycle(); retained=image;imageAspect=image.width.toFloat()/image.height
            glBindTexture(GL_TEXTURE_2D,flagTexture);GLUtils.texImage2D(GL_TEXTURE_2D,0,image,0)
        }
        val maxPixels=if(s.lowPower || s.quality=="low") 420 else if(s.quality=="high")1280 else 850
        if(s.quality!="auto") budget=1f
        val scale=min(1f,maxPixels*budget/max(w,h))
        try { target(max(1,(w*scale).toInt()),max(1,(h*scale).toInt())) }
        catch(e:Exception) {failure=e.message;return}
        glBindFramebuffer(GL_FRAMEBUFFER,fbo);glViewport(0,0,fw,fh)
        glEnable(GL_DEPTH_TEST);glDisable(GL_CULL_FACE)
        glClearColor(0f,0f,0f,0f);glClear(GL_COLOR_BUFFER_BIT or GL_DEPTH_BUFFER_BIT)
        val aspect=if(s.vertical) 1/imageAspect else imageAspect
        NativeCloth.fill(vertices,time,s.wind,aspect)
        glUseProgram(flagProgram)
        Matrix.setIdentityM(matrix,0)
        val fit=min(1.65f/aspect,1.55f*h/w)*zoom
        // Correct viewport aspect while retaining perspective through clip-space W.
        Matrix.scaleM(matrix,0,fit,fit*w/h,1f)
        Matrix.rotateM(matrix,0,pitch*180f/PI.toFloat(),1f,0f,0f)
        Matrix.rotateM(matrix,0,dragYaw*180f/PI.toFloat()+orbitAngle,0f,1f,0f)
        glUniformMatrix4fv(glGetUniformLocation(flagProgram,"m"),1,false,matrix,0)
        glUniform1i(glGetUniformLocation(flagProgram,"vertical"),if(s.vertical)1 else 0)
        glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,flagTexture);glUniform1i(glGetUniformLocation(flagProgram,"image"),0)
        vertices.position(0);glEnableVertexAttribArray(0);glVertexAttribPointer(0,3,GL_FLOAT,false,20,vertices)
        vertices.position(3);glEnableVertexAttribArray(1);glVertexAttribPointer(1,2,GL_FLOAT,false,20,vertices)
        glDrawArrays(GL_TRIANGLES,0,40*24*6)
        glBindFramebuffer(GL_FRAMEBUFFER,0);glViewport(0,0,w,h);glDisable(GL_DEPTH_TEST)
        glUseProgram(postProgram)
        glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,sceneTexture);glUniform1i(glGetUniformLocation(postProgram,"scene"),0)
        glActiveTexture(GL_TEXTURE1);glBindTexture(GL_TEXTURE_2D,glyphTexture);glUniform1i(glGetUniformLocation(postProgram,"glyphs"),1)
        val columns=s.cells.coerceIn(35f,if(s.lowPower)100f else 180f)
        glUniform2f(glGetUniformLocation(postProgram,"grid"),columns,max(12f,columns*h/w*.52f))
        glUniform1i(glGetUniformLocation(postProgram,"ascii"),if(s.ascii)1 else 0)
        glUniform1i(glGetUniformLocation(postProgram,"mono"),if(s.monochrome)1 else 0)
        glUniform1i(glGetUniformLocation(postProgram,"blocks"),if(s.blocks)1 else 0)
        glUniform1i(glGetUniformLocation(postProgram,"liftDark"),if(s.liftDark)1 else 0)
        glUniform1i(glGetUniformLocation(postProgram,"sextants"),if(s.sextants)1 else 0)
        quad.position(0);glVertexAttribPointer(0,2,GL_FLOAT,false,16,quad)
        quad.position(2);glVertexAttribPointer(1,2,GL_FLOAT,false,16,quad)
        glDrawArrays(GL_TRIANGLES,0,6)
        val elapsed=(System.nanoTime()-start)/1e9
        val fps=if(s.lowPower)min(24,s.fps) else s.fps.coerceIn(5,60)
        if(s.quality=="auto" && elapsed>1.0/fps && budget>.5f) budget=max(.5f,budget-.1f)
        val sleep=((1.0/fps-elapsed)*1000).toLong()
        if(sleep>0) Thread.sleep(sleep)
    }
    private fun texture():Int {
        val id=IntArray(1);glGenTextures(1,id,0);glBindTexture(GL_TEXTURE_2D,id[0])
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE)
        return id[0]
    }
    private fun program(v:String,f:String):Int {
        fun shader(type:Int,source:String):Int {
            val id=glCreateShader(type);glShaderSource(id,source);glCompileShader(id)
            val status=IntArray(1);glGetShaderiv(id,GL_COMPILE_STATUS,status,0)
            check(status[0]!=0) {glGetShaderInfoLog(id)};return id
        }
        val vs=shader(GL_VERTEX_SHADER,v);val fs=shader(GL_FRAGMENT_SHADER,f)
        val id=glCreateProgram();glAttachShader(id,vs);glAttachShader(id,fs);glLinkProgram(id)
        val status=IntArray(1);glGetProgramiv(id,GL_LINK_STATUS,status,0)
        check(status[0]!=0) {glGetProgramInfoLog(id)};glDeleteShader(vs);glDeleteShader(fs);return id
    }
    companion object {
        const val vertexShader="""#version 300 es
layout(location=0) in vec3 position;
layout(location=1) in vec2 texCoord;
uniform mat4 m;
out vec2 uv; out vec3 world;
void main(){ vec4 p=m*vec4(position,1.0); gl_Position=vec4(p.xy,p.z*.12,1.0-p.z*.15); uv=texCoord; world=position; }
"""
        const val flagShader="""#version 300 es
precision highp float;
in vec2 uv;in vec3 world;uniform sampler2D image;uniform bool vertical;out vec4 color;
void main(){ vec2 p=vertical?vec2(uv.y,1.0-uv.x):uv;vec4 tex=texture(image,p);if(tex.a<.4)discard;
vec3 n=normalize(cross(dFdx(world),dFdy(world)));float light=.48+.52*abs(dot(n,normalize(vec3(.25,.35,.9))));color=vec4(tex.rgb*light,1.0); }
"""
        const val quadShader="""#version 300 es
layout(location=0) in vec2 position;layout(location=1) in vec2 texCoord;out vec2 uv;
void main(){gl_Position=vec4(position,0.0,1.0);uv=texCoord;}
"""
        const val asciiShader="""#version 300 es
precision highp float;
in vec2 uv;uniform sampler2D scene;uniform sampler2D glyphs;uniform vec2 grid;uniform bool ascii;uniform bool mono;uniform bool blocks;uniform bool liftDark;uniform bool sextants;out vec4 color;
void main(){vec3 bg=vec3(.035,.055,.065);
// Each character cell has two columns and three rows of font-independent blocks.
vec2 sampleGrid=ascii&&sextants?grid*vec2(2.,3.):grid;
vec2 cell=(floor(uv*sampleGrid)+.5)/sampleGrid;vec4 c=texture(scene,ascii?cell:uv);
if(c.a<.1){color=vec4(bg,1);return;}float lum=dot(c.rgb,vec3(.2126,.7152,.0722));
// Lift luminance without changing hue; leave bright colours and transparency alone.
float lift=liftDark?max(0.,.28-lum):0.;
vec3 ink=mono?vec3(.35+lum*.65):min(vec3(1.),c.rgb+vec3(lift));float a=1.;
if(ascii&&!sextants){float index=blocks?12.:floor(clamp(.4+lum*.59,0.,.999)*16.);vec2 local=fract(uv*grid);a=texture(glyphs,vec2((index+local.x)/16.,1.-local.y)).a;}
color=vec4(mix(bg,ink,a),1.);}
"""
    }
}
