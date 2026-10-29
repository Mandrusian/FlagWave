#include <jni.h>
#include "cloth.h"
extern "C" JNIEXPORT void JNICALL Java_tech_mandrusia_flagwave_NativeCloth_fill(
    JNIEnv* env,jobject,jobject buffer,jfloat time,jfloat wind,jfloat aspect) {
    auto* out=static_cast<float*>(env->GetDirectBufferAddress(buffer));
    if(!out || env->GetDirectBufferCapacity(buffer)<flagwave::vertexCount*5) return;
    flagwave::fill(out,time,wind,aspect);
}
