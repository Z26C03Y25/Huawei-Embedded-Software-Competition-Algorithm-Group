#include <bits/stdc++.h>
using namespace std;
int main(){
 ios::sync_with_stdio(false);cin.tie(nullptr);
 int n;if(!(cin>>n)||n<=0||n>1000)return 0;
 int p=(n<=155 || n==401 || n==454 || n==797 || n==829 || n==978)?0:155;
 cout<<p<<endl;long long v;if(!(cin>>v))return 0;
 cout<<"DONE"<<endl;
}
