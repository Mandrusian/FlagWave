#pragma once
#include <cmath>
namespace flagwave {
constexpr int columns=40, rows=24, vertexCount=columns*rows*6;
inline void vertex(float* out, float u, float v, float t, float wind, float aspect) {
    const float phase=10*u-t*3.3f+2.2f*v;
    out[0]=(u-wind*.025f*u*std::cos(phase)-.5f)*aspect;
    out[1]=.5f-v+wind*u*(.08f*std::sin(8*u-t*2.5f+3*v)-.055f*u);
    out[2]=wind*u*(.29f*std::sin(phase)+.10f*std::sin(17*u-t*5.1f-5*v));
    out[3]=u; out[4]=v;
}
inline void fill(float* out,float t,float wind,float aspect) {
    int index=0;
    for(int y=0;y<rows;y++) for(int x=0;x<columns;x++) {
        const int dx[]={0,1,0,1,1,0}, dy[]={0,0,1,0,1,1};
        for(int i=0;i<6;i++,index+=5)
            vertex(out+index,float(x+dx[i])/columns,float(y+dy[i])/rows,t,wind,aspect);
    }
}
}
