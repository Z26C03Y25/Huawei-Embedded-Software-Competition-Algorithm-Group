#include <bits/stdc++.h>
using namespace std;
int main() {
    ios::sync_with_stdio(false);cin.tie(nullptr);
    int n;if(!(cin>>n)||n<=0||n>1000)return 0;
    int lo=min(0,n-1),hi=min(49,n-1),winner=-1;
    long long top=-1;
    for(int x=lo;x<=hi;++x){
        cout<<x<<endl;
        long long v;if(!(cin>>v))return 0;
        if(v>top||(v==top&&(winner<0||abs(2*x-(n-1))<abs(2*winner-(n-1))||
            (abs(2*x-(n-1))==abs(2*winner-(n-1))&&x<winner)))){
            top=v;winner=x;
        }
    }
    if(winner!=hi){cout<<winner<<endl;long long v;if(!(cin>>v))return 0;}
    cout<<"DONE"<<endl;
}
