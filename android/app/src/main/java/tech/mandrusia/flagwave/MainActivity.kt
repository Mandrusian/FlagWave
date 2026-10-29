package tech.mandrusia.flagwave

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.compose.setContent
import androidx.compose.animation.AnimatedContent
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlin.math.abs

class MainActivity:ComponentActivity() {
    override fun onCreate(savedInstanceState:Bundle?) {
        super.onCreate(savedInstanceState);enableEdgeToEdge()
        val store=FlagStore(this)
        setContent {
            MaterialTheme(colorScheme=darkColorScheme(primary=Color(0xFF8DE2CF),onPrimary=Color(0xFF00382E),primaryContainer=Color(0xFF175448),secondary=Color(0xFFB2CCC5),background=Color(0xFF0D1418),surface=Color(0xFF111C20),surfaceVariant=Color(0xFF233238))) {
                FlagWave(store)
            }
        }
    }
    @OptIn(ExperimentalMaterial3Api::class)
    @Composable private fun FlagWave(store:FlagStore) {
        var flags by remember {mutableStateOf(store.all())}
        var selected by remember {mutableStateOf(flags.find {it.id==store.prefs.getString("selected","red-eureka")}?:flags.first {it.id=="red-eureka"})}
        var settings by remember {mutableStateOf(store.options())}
        var favourites by remember {mutableStateOf(store.prefs.getStringSet("favourites",emptySet())!!.toSet())}
        var tab by remember {mutableIntStateOf(0)}
        var fullscreen by remember {mutableStateOf(false)}
        var sheet by remember {mutableStateOf(false)}
        var info by remember {mutableStateOf<Flag?>(null)}
        var importing by remember {mutableStateOf(false)}
        val scope=rememberCoroutineScope();val snack=remember {SnackbarHostState()}
        fun update(o:RenderOptions) {settings=o;store.save(o)}
        fun select(flag:Flag) {selected=flag;store.prefs.edit().putString("selected",flag.id).apply();tab=0}
        fun favourite(flag:Flag) {favourites=if(flag.id in favourites) favourites-flag.id else favourites+flag.id;store.prefs.edit().putStringSet("favourites",favourites).apply()}
        val picker=rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri ->
            if(uri!=null) scope.launch {
                importing=true
                try {val flag=withContext(Dispatchers.IO) {store.import(uri)};flags=store.all();select(flag);snack.showSnackbar("Image added to your library")}
                catch(e:Exception) {snack.showSnackbar(e.message?:"Could not import image")}
                finally {importing=false}
            }
        }
        LaunchedEffect(fullscreen) {
            val bars=WindowCompat.getInsetsController(window,window.decorView)
            if(fullscreen) {bars.hide(WindowInsetsCompat.Type.systemBars());bars.systemBarsBehavior=androidx.core.view.WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE}
            else bars.show(WindowInsetsCompat.Type.systemBars())
        }
        BackHandler(fullscreen || tab!=0) {fullscreen=false;tab=0}
        Scaffold(
            containerColor=MaterialTheme.colorScheme.background,
            topBar={if(!fullscreen) CenterAlignedTopAppBar(title={Text("FlagWave",fontWeight=FontWeight.Bold)},actions={IconButton(onClick={info=selected}) {Icon(Icons.Default.Info,"Flag details")}})},
            bottomBar={if(!fullscreen) NavigationBar {
                NavigationBarItem(tab==0,{tab=0},icon={Icon(Icons.Default.Waves,null)},label={Text("Stage")})
                NavigationBarItem(tab==1,{tab=1},icon={Icon(Icons.Default.Flag,null)},label={Text("Library")})
                NavigationBarItem(tab==2,{tab=2},icon={Icon(Icons.Default.Tune,null)},label={Text("Controls")})
            }}, snackbarHost={SnackbarHost(snack)}
        ) {padding ->
            Box(Modifier.fillMaxSize().padding(if(fullscreen) PaddingValues(0.dp) else padding)) {
                when(tab) {
                    0 -> Stage(store,selected,settings,fullscreen,selected.id in favourites,
                        onOptions={update(it)},onFullscreen={fullscreen=!fullscreen},onControls={sheet=true},onFavourite={favourite(selected)})
                    1 -> Library(store,flags,favourites,importing,onSelect={select(it)},onFavourite={favourite(it)},onInfo={info=it},onImport={picker.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))})
                    2 -> Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(24.dp)) {
                        Text("Make it yours",style=MaterialTheme.typography.headlineLarge,fontWeight=FontWeight.Bold)
                        Text("A little wind. A different perspective.",color=MaterialTheme.colorScheme.onSurfaceVariant)
                        Spacer(Modifier.height(24.dp));Controls(settings) {update(it)}
                    }
                }
            }
        }
        if(sheet) ModalBottomSheet(onDismissRequest={sheet=false}) {
            Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(horizontal=24.dp).padding(bottom=40.dp)) {
                Text("Motion & appearance",style=MaterialTheme.typography.headlineSmall,fontWeight=FontWeight.Bold)
                Spacer(Modifier.height(16.dp));Controls(settings) {update(it)}
            }
        }
        info?.let {flag -> AlertDialog(onDismissRequest={info=null},title={Text(flag.name)},text={Column(Modifier.verticalScroll(rememberScrollState())) {
            Text(flag.tags.joinToString(" · "));if(flag.period.isNotBlank()) {Spacer(Modifier.height(12.dp));Text(flag.period)}
            if(flag.source.isNotBlank()) {Spacer(Modifier.height(16.dp));Text("Source",fontWeight=FontWeight.Bold);androidx.compose.foundation.text.selection.SelectionContainer {Text(flag.source)}}
            if(flag.credit.isNotBlank()) {Spacer(Modifier.height(12.dp));Text(flag.credit)}
            if(flag.license.isNotBlank()) Text(flag.license,color=MaterialTheme.colorScheme.primary)
            if(flag.id=="red-eureka") {Spacer(Modifier.height(12.dp));Text("Red-field reconstruction of the public-domain Eureka design; not attributed to one organisation.")}
        }},confirmButton={TextButton(onClick={info=null}) {Text("Done")}}) }
    }
}

@Composable private fun Stage(store:FlagStore,flag:Flag,options:RenderOptions,fullscreen:Boolean,favourite:Boolean,onOptions:(RenderOptions)->Unit,onFullscreen:()->Unit,onControls:()->Unit,onFavourite:()->Unit) {
    var view by remember {mutableStateOf<FlagSurface?>(null)}
    var loading by remember {mutableStateOf(true)}
    var error by remember {mutableStateOf<String?>(null)}
    val owner=LocalLifecycleOwner.current
    LaunchedEffect(view,flag.id) {
        val target=view?:return@LaunchedEffect
        loading=true;error=null
        try {val bitmap=withContext(Dispatchers.IO) {store.bitmap(flag)};target.engine.pending.getAndSet(bitmap)?.recycle()}
        catch(e:Exception) {error=e.message?:"Could not load flag"}
        finally {loading=false}
    }
    LaunchedEffect(view,options) {view?.engine?.options?.set(options)}
    LaunchedEffect(view) {
        while(true) {kotlinx.coroutines.delay(1000);view?.engine?.failure?.let {error=it}}
    }
    DisposableEffect(view,owner) {
        val surface=view
        val observer=LifecycleEventObserver {_,event -> when(event) {Lifecycle.Event.ON_RESUME -> surface?.onResume();Lifecycle.Event.ON_PAUSE -> surface?.onPause();else -> Unit} }
        owner.lifecycle.addObserver(observer)
        if(owner.lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED)) surface?.onResume()
        onDispose {owner.lifecycle.removeObserver(observer);surface?.onPause()}
    }
    BoxWithConstraints(Modifier.fillMaxSize()) {
    val compact=maxHeight<360.dp
    Column(Modifier.fillMaxSize().padding(if(fullscreen) 0.dp else if(compact) 12.dp else 20.dp),verticalArrangement=Arrangement.spacedBy(if(compact) 8.dp else 16.dp)) {
        if(!fullscreen && !compact) {
            Row(verticalAlignment=Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text(if(options.paused) "PAUSED" else "LIVE CANVAS",color=MaterialTheme.colorScheme.primary,style=MaterialTheme.typography.labelMedium)
                    Text(flag.name,style=MaterialTheme.typography.headlineSmall,fontWeight=FontWeight.Bold,maxLines=2,overflow=TextOverflow.Ellipsis)
                }
                IconButton(onClick=onFavourite) {Icon(if(favourite) Icons.Default.Favorite else Icons.Default.FavoriteBorder,"Toggle favourite",tint=MaterialTheme.colorScheme.primary)}
            }
        }
        Surface(Modifier.weight(1f).fillMaxWidth(),shape=RoundedCornerShape(if(fullscreen) 0.dp else 28.dp),color=Color(0xFF090E11)) {
            Box(Modifier.fillMaxSize()) {
                AndroidView(factory={context -> FlagSurface(context).also {it.engine.options.set(options);view=it}},modifier=Modifier.fillMaxSize())
                if(loading) CircularProgressIndicator(Modifier.align(Alignment.Center))
                error?.let {Text(it,Modifier.align(Alignment.Center).padding(24.dp),color=MaterialTheme.colorScheme.error)}
                FilledTonalIconButton(onClick=onFullscreen,modifier=Modifier.align(Alignment.TopEnd).padding(12.dp)) {Icon(if(fullscreen) Icons.Default.FullscreenExit else Icons.Default.Fullscreen,if(fullscreen) "Exit fullscreen" else "Fullscreen")}
                if(fullscreen) FilledTonalIconButton(onClick={onOptions(options.copy(paused=!options.paused))},modifier=Modifier.align(Alignment.BottomEnd).padding(20.dp)) {Icon(if(options.paused) Icons.Default.PlayArrow else Icons.Default.Pause,"Pause or resume")}
            }
        }
        if(!fullscreen) {
            if(!compact) Text("Drag to orbit · Pinch to zoom",Modifier.align(Alignment.CenterHorizontally),style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
            Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(12.dp)) {
                FilledIconButton(onClick={onOptions(options.copy(paused=!options.paused))},modifier=Modifier.size(56.dp)) {Icon(if(options.paused) Icons.Default.PlayArrow else Icons.Default.Pause,if(options.paused) "Resume" else "Pause")}
                FilledTonalButton(onClick={onOptions(options.copy(orbit=!options.orbit))},modifier=Modifier.weight(1f).height(56.dp)) {Icon(Icons.Default.RotateRight,null);Spacer(Modifier.width(8.dp));Text(if(options.orbit) "Orbit on" else "Orbit off")}
                FilledTonalIconButton(onClick=onControls,modifier=Modifier.size(56.dp)) {Icon(Icons.Default.Tune,"Motion and appearance")}
            }
        }
    }
    }
}

@Composable private fun Library(store:FlagStore,flags:List<Flag>,favourites:Set<String>,importing:Boolean,onSelect:(Flag)->Unit,onFavourite:(Flag)->Unit,onInfo:(Flag)->Unit,onImport:()->Unit) {
    var search by remember {mutableStateOf("")};var category by remember {mutableStateOf("All")}
    val categories=remember(flags) {listOf("All","Favourites","My images")+flags.flatMap {it.tags}.distinct().filter {it!="My images"}.sorted()}
    val filtered=remember(flags,favourites,search,category) {flags.filter {f ->
        (category=="All" || category=="Favourites" && f.id in favourites || category in f.tags) &&
            search.lowercase().split(' ').all {word -> word in "${f.id} ${f.name} ${f.tags.joinToString(" ")} ${f.period}".lowercase()}
    }}
    Column(Modifier.fillMaxSize(),verticalArrangement=Arrangement.spacedBy(12.dp)) {
        Row(Modifier.padding(horizontal=20.dp),verticalAlignment=Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {Text("Find your flag",style=MaterialTheme.typography.headlineSmall,fontWeight=FontWeight.Bold);Text("${flags.size} designs. Your perspective.",color=MaterialTheme.colorScheme.onSurfaceVariant)}
            FilledTonalButton(onClick=onImport,enabled=!importing) {Icon(Icons.Default.Add,null);Text(if(importing) "Adding…" else "Import")}
        }
        OutlinedTextField(search,{search=it},Modifier.fillMaxWidth().padding(horizontal=20.dp),placeholder={Text("Search flags, eras, ideologies…")},leadingIcon={Icon(Icons.Default.Search,null)},singleLine=true,shape=RoundedCornerShape(24.dp))
        LazyRow(contentPadding=PaddingValues(horizontal=20.dp),horizontalArrangement=Arrangement.spacedBy(8.dp)) {items(categories) {c -> FilterChip(selected=category==c,onClick={category=c},label={Text(c)})}}
        if(filtered.isEmpty()) Box(Modifier.fillMaxSize(),contentAlignment=Alignment.Center) {Text(if(category=="My images") "Import an image to make it wave." else "No flags found. Try another search.")}
        else LazyVerticalGrid(GridCells.Adaptive(155.dp),contentPadding=PaddingValues(start=20.dp,end=20.dp,bottom=20.dp),horizontalArrangement=Arrangement.spacedBy(12.dp),verticalArrangement=Arrangement.spacedBy(12.dp)) {
            items(filtered,key={it.id}) {flag ->
                Card(onClick={onSelect(flag)},shape=RoundedCornerShape(22.dp),colors=CardDefaults.cardColors(containerColor=MaterialTheme.colorScheme.surface)) {
                    var bitmap by remember(flag.id) {mutableStateOf<android.graphics.Bitmap?>(null)}
                    LaunchedEffect(flag.id) {bitmap=withContext(Dispatchers.IO) {runCatching {store.bitmap(flag,320)}.getOrNull()}}
                    Box(Modifier.fillMaxWidth().height(100.dp).background(Color(0xFF19262B))) {bitmap?.let {Image(it.asImageBitmap(),flag.name,Modifier.fillMaxSize().padding(18.dp),contentScale=ContentScale.Fit)}}
                    Column(Modifier.padding(start=12.dp,end=12.dp,top=12.dp)) {
                        Text(flag.name,fontWeight=FontWeight.SemiBold,maxLines=2,overflow=TextOverflow.Ellipsis,style=MaterialTheme.typography.titleSmall)
                        Text(flag.tags.firstOrNull()?:"",style=MaterialTheme.typography.labelSmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.End) {
                        IconButton(onClick={onInfo(flag)}) {Icon(Icons.Default.Info,"Details for ${flag.name}",Modifier.size(18.dp))}
                        IconButton(onClick={onFavourite(flag)}) {Icon(if(flag.id in favourites) Icons.Default.Favorite else Icons.Default.FavoriteBorder,"Favourite ${flag.name}",Modifier.size(18.dp),tint=MaterialTheme.colorScheme.primary)}
                    }
                }
            }
        }
    }
}
@Composable private fun Controls(o:RenderOptions,onChange:(RenderOptions)->Unit) {
    ControlSwitch("Automatic orbit","Slowly circle the waving flag",o.orbit) {onChange(o.copy(orbit=it))}
    Text("Orbit speed · ${"%.1f".format(abs(o.speed))}°/s",Modifier.padding(top=12.dp),fontWeight=FontWeight.SemiBold)
    Slider(abs(o.speed),{onChange(o.copy(speed=it*(if(o.speed<0)-1 else 1)))},valueRange=.5f..30f)
    ControlSwitch("Reverse direction","Rotate the other way",o.speed<0) {onChange(o.copy(speed=abs(o.speed)*(if(it)-1 else 1)))}
    Text("Wind · ${"%.1f".format(o.wind)}",Modifier.padding(top=12.dp),fontWeight=FontWeight.SemiBold)
    Slider(o.wind,{onChange(o.copy(wind=it))},valueRange=0f..2.5f)
    HorizontalDivider(Modifier.padding(vertical=16.dp))
    ControlSwitch("ASCII rendering","A terminal-inspired character canvas",o.ascii) {onChange(o.copy(ascii=it))}
    ControlSwitch("Monochrome","Use light characters instead of flag colours",o.monochrome) {onChange(o.copy(monochrome=it))}
    Text("Character detail · ${o.cells.toInt()} columns",Modifier.padding(top=12.dp),fontWeight=FontWeight.SemiBold)
    Slider(o.cells,{onChange(o.copy(cells=it))},valueRange=35f..180f)
    ControlSwitch("Vertical artwork","Rotate the image into a hanging banner",o.vertical) {onChange(o.copy(vertical=it))}
    HorizontalDivider(Modifier.padding(vertical=16.dp))
    ControlSwitch("Battery saver","Lower render resolution and frame rate",o.lowPower) {onChange(o.copy(lowPower=it))}
    TextButton(onClick={onChange(RenderOptions())}) {Text("Restore default controls")}
}
@Composable private fun ControlSwitch(title:String,subtitle:String,checked:Boolean,onChange:(Boolean)->Unit) {
    Row(Modifier.fillMaxWidth().padding(vertical=8.dp),verticalAlignment=Alignment.CenterVertically) {
        Column(Modifier.weight(1f).padding(end=16.dp)) {Text(title,fontWeight=FontWeight.SemiBold);Text(subtitle,style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)}
        Switch(checked,onChange)
    }
}
