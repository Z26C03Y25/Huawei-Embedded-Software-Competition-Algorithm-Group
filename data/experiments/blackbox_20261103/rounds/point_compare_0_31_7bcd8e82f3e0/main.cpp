#include <bits/stdc++.h>
using namespace std;
int main(){
    ios::sync_with_stdio(false);cin.tie(nullptr);
    int n;if(!(cin>>n)||n<=0||n>1000)return 0;
    cout<<0<<endl;long long a;if(!(cin>>a))return 0;
    const int p=min(31,n-1);
    cout<<p<<endl;long long b;if(!(cin>>b))return 0;
    const bool win=b>a||(b==a&&abs(2*p-(n-1))<abs(n-1));
    if(!win){cout<<0<<endl;long long c;if(!(cin>>c))return 0;}
    cout<<"DONE"<<endl;
}
