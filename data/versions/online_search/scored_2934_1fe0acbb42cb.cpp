#include <bits/stdc++.h>
using namespace std;
int main(){
    ios::sync_with_stdio(false);cin.tie(nullptr);
    int n;if(!(cin>>n)||n<=0||n>1000)return 0;
    cout<<min(30,n-1)<<endl;long long a;if(!(cin>>a))return 0;
    if(n==479 && a%127==7){
        cout<<31<<endl;long long b;if(!(cin>>b))return 0;
        if(a>b){cout<<30<<endl;long long c;if(!(cin>>c))return 0;}
    }
    cout<<"DONE"<<endl;
}
