#include "../app/src/main/cpp/cloth.h"
#include <cassert>
#include <vector>
int main() {
    float a[5],b[5];
    flagwave::vertex(a,0,.3,0,1,1.5);flagwave::vertex(b,0,.3,8,1,1.5);
    for(int i=0;i<5;i++) assert(a[i]==b[i]);
    flagwave::vertex(a,1,.3,0,1,1.5);flagwave::vertex(b,1,.3,8,1,1.5);
    assert(a[2]!=b[2]);
    const int count=flagwave::vertexCount*5;
    std::vector<float> vertices(count+1,1234);
    flagwave::fill(vertices.data(),100,2.5,2);
    assert(vertices[count]==1234);
    for(int i=0;i<count;i++) assert(std::isfinite(vertices[i]));
    for(int i=0;i<count;i+=5) {assert(vertices[i+3]>=0 && vertices[i+3]<=1);assert(vertices[i+4]>=0 && vertices[i+4]<=1);}
}
