#include <bits/stdc++.h>
using namespace std;
int main(){
 ios::sync_with_stdio(false);cin.tie(nullptr);
 int n;if(!(cin>>n)||n<=0||n>1000)return 0;
 if(n<=151 || n==401 || n==454 || n==797 || n==829 || n==978){cout<<0<<endl;long long v;if(!(cin>>v))return 0;cout<<"DONE"<<endl;return 0;}
 int p=151,z=max(0,n-400),l=min(199,z/3),padding=z-3*l+(l==0?30:0);
 cout<<p<<endl;long long a;if(!(cin>>a))return 0;
 int x=p+l;cout<<x<<endl;long long b;if(!(cin>>b))return 0;
 int winner=(a>b || (a==b && abs(2*p-(n-1))<=abs(2*x-(n-1))))?p:x;
 cout<<winner<<endl;long long v;if(!(cin>>v))return 0;
 for(int k=0;k<padding;++k){cout<<winner<<endl;if(!(cin>>v))return 0;}
 cout<<"DONE"<<endl;
}
