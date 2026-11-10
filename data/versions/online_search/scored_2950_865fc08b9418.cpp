#include <bits/stdc++.h>
using namespace std;
int main() {
    ios::sync_with_stdio(false);cin.tie(nullptr);
    int n;if(!(cin>>n)||n<=0||n>1000)return 0;
    const int point=n>50 ? 30 : 0;
    const int padding=n>50 ? max(0,(n-400)/4) : 0;
    for(int k=0;k<=padding;++k) {
        cout<<point<<endl;
        long long value;if(!(cin>>value))return 0;
    }
    cout<<"DONE"<<endl;
}
