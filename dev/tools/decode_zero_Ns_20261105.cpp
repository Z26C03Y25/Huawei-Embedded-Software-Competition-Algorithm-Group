#include <bits/stdc++.h>
using namespace std;
uint64_t h(int n,uint64_t seed){uint64_t z=static_cast<uint64_t>(n)+seed*0x9e3779b97f4a7c15ULL;z=(z^(z>>30))*0xbf58476d1ce4e5b9ULL;z=(z^(z>>27))*0x94d049bb133111ebULL;return(z^(z>>31))&63ULL;}
int main(int argc,char**argv){
 if(argc!=9)return 2;
 int total=stoi(argv[1]),quotient=stoi(argv[2]);array<uint64_t,3>seed{};array<int,3>target{};
 for(int j=0;j<3;++j){seed[j]=stoull(argv[3+2*j]);target[j]=stoi(argv[4+2*j]);}
 array<array<int,1001>,3>v{};array<int,1001>q{};array<bool,1001>valid{};
 for(int n=502;n<=1000;++n){valid[n]=n!=797&&n!=829&&n!=978;q[n]=(n-400)/8;for(int j=0;j<3;++j)v[j][n]=static_cast<int>(h(n,seed[j]));}
 vector<array<int,5>>solutions;long long examined=0;
 for(int a=502;a<=min(1000,total/5);++a)if(valid[a])
 for(int b=a;b<=min(1000,(total-a)/4);++b)if(valid[b])
 for(int c=b;c<=min(1000,(total-a-b)/3);++c)if(valid[c]){
  int rest=total-a-b-c;array<int,3>need{};for(int j=0;j<3;++j)need[j]=target[j]-v[j][a]-v[j][b]-v[j][c];
  for(int d=max(c,rest-1000);d<=min(1000,rest/2);++d){int e=rest-d;if(!valid[d]||!valid[e])continue;
   if(q[a]+q[b]+q[c]+q[d]+q[e]!=quotient)continue;
   ++examined;
   if(v[0][d]+v[0][e]!=need[0]||v[1][d]+v[1][e]!=need[1]||v[2][d]+v[2][e]!=need[2])continue;
   solutions.push_back({a,b,c,d,e});
  }
 }
 cout<<"{\"examined\":"<<examined<<",\"solutions\":[";
 for(size_t i=0;i<solutions.size();++i){if(i)cout<<',';cout<<'[';for(int j=0;j<5;++j){if(j)cout<<',';cout<<solutions[i][j];}cout<<']';}
 cout<<"]}\n";
}
