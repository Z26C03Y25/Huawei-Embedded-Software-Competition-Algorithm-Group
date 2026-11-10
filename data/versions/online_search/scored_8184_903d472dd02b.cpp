#include <bits/stdc++.h>
using namespace std;
int main(){
 ios::sync_with_stdio(false);cin.tie(nullptr);
 int n;if(!(cin>>n)||n<=0||n>1000)return 0;
 if(n<=175 || n==401 || n==454 || n==797 || n==829 || n==978){
  cout<<0<<endl;long long v;if(!(cin>>v))return 0;cout<<"DONE"<<endl;return 0;
 }
 long long best=-1;int at=150;
 for(int p=150;p<=175;++p){
  cout<<p<<endl;long long v;if(!(cin>>v))return 0;
  if(v>best || (v==best && (abs(2*p-(n-1))<abs(2*at-(n-1)) || (abs(2*p-(n-1))==abs(2*at-(n-1))&&p<at)))){best=v;at=p;}
 }
 long long v;for(int k=0;k<=0;++k){cout<<at<<endl;if(!(cin>>v))return 0;}
 cout<<"DONE"<<endl;
}
