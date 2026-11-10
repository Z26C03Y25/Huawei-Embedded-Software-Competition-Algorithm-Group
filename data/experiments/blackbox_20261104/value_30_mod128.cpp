#include <bits/stdc++.h>
using namespace std;
int main() {
    ios::sync_with_stdio(false);cin.tie(nullptr);
    int n;if(!(cin>>n)||n<=0||n>1000)return 0;
    const int p=n>50 ? 30 : 0;
    cout<<p<<endl;long long value;if(!(cin>>value))return 0;
    const int padding=n>50 ? static_cast<int>(value%128) : 0;
    for(int i=0;i<padding;++i) {cout<<p<<endl;long long reply;if(!(cin>>reply))return 0;}
    cout<<"DONE"<<endl;
}
