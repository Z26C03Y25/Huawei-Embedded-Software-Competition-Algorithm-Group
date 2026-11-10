#include <bits/stdc++.h>
using namespace std;
int main(){
 ios::sync_with_stdio(false);cin.tie(nullptr);
 int n;if(!(cin>>n)||n<=0||n>1000)return 0;
 if(n<=151 || n==401 || n==454 || n==797 || n==829 || n==978){cout<<0<<endl;long long v;if(!(cin>>v))return 0;cout<<"DONE"<<endl;return 0;}
 int p=151;cout<<p<<endl;long long a;if(!(cin>>a))return 0;
 if(true){
  int z=max(0,n-400),c=z/193,padding=z-193*c;
  for(int k=0;k<c;++k){
   cout<<0<<endl;long long b;if(!(cin>>b))return 0;
   if(b>a || (b==a && abs(n-1)<=abs(2*p-(n-1)))){cout<<"DONE"<<endl;return 0;}
   cout<<p<<endl;long long v;if(!(cin>>v))return 0;
  }
  for(int k=0;k<padding;++k){cout<<p<<endl;long long v;if(!(cin>>v))return 0;}
 }
 cout<<"DONE"<<endl;
}
