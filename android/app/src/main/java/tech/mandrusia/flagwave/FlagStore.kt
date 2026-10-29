package tech.mandrusia.flagwave

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import androidx.exifinterface.media.ExifInterface
import android.net.Uri
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.security.MessageDigest

data class Flag(val id:String,val name:String,val path:String,val tags:List<String>,val period:String="",val source:String="",val credit:String="",val license:String="")
class FlagStore(val context:Context) {
    val prefs=context.getSharedPreferences("flagwave",Context.MODE_PRIVATE)
    private val imports=File(context.filesDir,"imports").apply {mkdirs()}
    val bundled:List<Flag> = buildList {
        val countries=JSONObject(context.assets.open("countries.json").bufferedReader().use {it.readText()})
        countries.keys().forEach {id -> add(Flag(id,countries.getString(id),"flags/$id.png",listOf("Countries"))) }
        val archive=JSONArray(context.assets.open("archive.json").bufferedReader().use {it.readText()})
        for(i in 0 until archive.length()) {
            val e=archive.getJSONObject(i);val tags=e.getJSONArray("tags")
            add(Flag(e.getString("id"),e.getString("name"),e.getString("asset"),(0 until tags.length()).map {tags.getString(it)},e.optString("period"),e.optString("source"),e.optString("credit"),e.optString("license")))
        }
    }.sortedBy {it.name.lowercase()}
    fun all():List<Flag> = (bundled+imports.listFiles().orEmpty().filter {it.extension=="png"}.map {
        Flag("import:${it.name}",prefs.getString("name:${it.name}",it.nameWithoutExtension)?:it.nameWithoutExtension,it.absolutePath,listOf("My images"))
    }).sortedBy {it.name.lowercase()}
    fun bitmap(flag:Flag,limit:Int=1024):Bitmap {
        fun stream()=if(flag.path.startsWith("/")) File(flag.path).inputStream() else context.assets.open(flag.path)
        val bounds=BitmapFactory.Options().apply {inJustDecodeBounds=true}
        stream().use {BitmapFactory.decodeStream(it,null,bounds)}
        check(bounds.outWidth>0 && bounds.outHeight>0) {"Unsupported image"}
        var sample=1
        while(bounds.outWidth/sample>limit || bounds.outHeight/sample>limit) sample*=2
        return stream().use {BitmapFactory.decodeStream(it,null,BitmapFactory.Options().apply {inSampleSize=sample})}?:error("Cannot decode image")
    }
    fun import(uri:Uri):Flag {
        val bounds=BitmapFactory.Options().apply {inJustDecodeBounds=true}
        context.contentResolver.openInputStream(uri).use {BitmapFactory.decodeStream(it,null,bounds)}
        check(bounds.outWidth>0 && bounds.outHeight>0) {"Choose a PNG, JPEG, WebP or another supported image"}
        var sample=1
        while(bounds.outWidth/sample>1024 || bounds.outHeight/sample>1024) sample*=2
        var image=context.contentResolver.openInputStream(uri).use {BitmapFactory.decodeStream(it,null,BitmapFactory.Options().apply {inSampleSize=sample})}?:error("Cannot open image")
        val orientation=context.contentResolver.openInputStream(uri).use {stream ->
            if(stream==null) ExifInterface.ORIENTATION_NORMAL else runCatching {ExifInterface(stream).getAttributeInt(ExifInterface.TAG_ORIENTATION,ExifInterface.ORIENTATION_NORMAL)}.getOrDefault(ExifInterface.ORIENTATION_NORMAL)
        }
        val matrix=Matrix()
        when(orientation) {
            ExifInterface.ORIENTATION_FLIP_HORIZONTAL -> matrix.setScale(-1f,1f)
            ExifInterface.ORIENTATION_ROTATE_180 -> matrix.setRotate(180f)
            ExifInterface.ORIENTATION_FLIP_VERTICAL -> matrix.setScale(1f,-1f)
            ExifInterface.ORIENTATION_TRANSPOSE -> {matrix.setRotate(90f);matrix.postScale(-1f,1f)}
            ExifInterface.ORIENTATION_ROTATE_90 -> matrix.setRotate(90f)
            ExifInterface.ORIENTATION_TRANSVERSE -> {matrix.setRotate(-90f);matrix.postScale(-1f,1f)}
            ExifInterface.ORIENTATION_ROTATE_270 -> matrix.setRotate(270f)
        }
        if(!matrix.isIdentity) {
            val rotated=Bitmap.createBitmap(image,0,0,image.width,image.height,matrix,true)
            if(rotated!==image) image.recycle()
            image=rotated
        }
        val bytes=java.io.ByteArrayOutputStream().use {out -> image.compress(Bitmap.CompressFormat.PNG,100,out);out.toByteArray()}
        image.recycle()
        val hash=MessageDigest.getInstance("SHA-256").digest(bytes).take(12).joinToString("") {"%02x".format(it)}
        val dest=File(imports,"$hash.png");dest.writeBytes(bytes)
        var name="Imported flag"
        context.contentResolver.query(uri,arrayOf(android.provider.OpenableColumns.DISPLAY_NAME),null,null,null)?.use {cursor ->
            if(cursor.moveToFirst()) name=cursor.getString(0).substringBeforeLast('.',cursor.getString(0))
        }
        prefs.edit().putString("name:${dest.name}",name).apply()
        return Flag("import:${dest.name}",name,dest.absolutePath,listOf("My images"))
    }
    fun options()=RenderOptions(orbit=prefs.getBoolean("orbit",true),speed=prefs.getFloat("speed",6f),wind=prefs.getFloat("wind",1f),ascii=prefs.getBoolean("ascii",true),monochrome=prefs.getBoolean("mono",false),vertical=prefs.getBoolean("vertical",false),lowPower=prefs.getBoolean("lowPower",false),cells=prefs.getFloat("cells",100f),fps=prefs.getInt("fps",60),quality=prefs.getString("quality","auto")?:"auto",liftDark=prefs.getBoolean("liftDark",true),sextants=prefs.getBoolean("sextants",false),blocks=prefs.getBoolean("blocks",false),layout=prefs.getString("layout","auto")?:"auto")
    fun save(o:RenderOptions) {prefs.edit().putBoolean("orbit",o.orbit).putFloat("speed",o.speed).putFloat("wind",o.wind).putBoolean("ascii",o.ascii).putBoolean("mono",o.monochrome).putBoolean("vertical",o.vertical).putBoolean("lowPower",o.lowPower).putFloat("cells",o.cells).putInt("fps",o.fps).putString("quality",o.quality).putBoolean("liftDark",o.liftDark).putBoolean("sextants",o.sextants).putBoolean("blocks",o.blocks).putString("layout",o.layout).apply()}
}
