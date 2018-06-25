# devops

### Step 1: Upgrade Packages
```
yum update
yum groupinstall "Development Tools"
```
### Step 2: Installing Recommended Packages
```
yum install gcc-c++ patch readline readline-devel zlib zlib-devel 
yum install libyaml-devel libffi-devel openssl-devel make 
yum install bzip2 autoconf automake libtool bison iconv-devel
```
### Step 3: Install RVM ( Ruby Version Manager ) 
```
curl -L get.rvm.io | bash -s stable
```
### Step 4: Setup RVM Environment 
```
source /etc/profile.d/rvm.sh
```
### Step 5: Install Required Ruby Version
```
rvm install 1.9.3
```
### Step 6: Install Another Version ( if Required ) 
```
rvm install 1.8.6
```
### Step 7: Setup Default Ruby Version
```
rvm use 1.9.3 --default 
```
### Step 8: Check Current Ruby Version 
```
ruby --version
```

### python27 and pip install
```
sudo yum update 
sudo yum install centos-release-scl 
sudo yum install python27 # install Python 2.7

scl enable python27 bash

cd /opt/rh/python27/root/usr/bin/
sudo LD_LIBRARY_PATH=$LD_LIBRARY_PATH ./easy_install-2.7 pip

sudo LD_LIBRARY_PATH=$LD_LIBRARY_PATH ./pip2.7 install requests 

git clone https://github.com/instagrambot/instabot.git --recursive && pip install "fabric<2" #### install fabric
```
### Fabric rpm builder

The fabric file creates the below rpms. This fabric is intended to be run by jenkins but by installing fabric pip install fabric it can be run locally as well (useful for testing). It requires ssh root access 96.118.31.134

notification_device_host_consumer
pr_device_interface_data
pr_device_status_data
pr_device_traffic_data
odphook
xap
The repo server is located at http://96.118.31.134/repos/xpc/

To add the repo.. add xpc.repo to /etc/yum.repos.d
```
[xpc]
name=xpc
baseurl=http://96.118.31.134/repos/xpc
enabled=1
gpgcheck=0
metadata_expire=0
```
##Naming convention of rpms

```
{REPO_NAME}-{VERSION}-{BUILD_NUMBER}.x86_64.rpm

The {BUILD_NUMBER} is autoincremented based on latest build of that repo and version

The {VERSION} is determined by the branch and the sprint_versions.txt located in this repo

Example: xap-16.10.2-43.x86_64.rpm
```

## Quick yum examples
```
To install latest

yum install xap

To update to latest

yum update xap

To install an older version (if for example n-1 is needed)

yum install xap-16.10.1

To downgrade (if need to revert or wrong version installed)

yum downgrade xap-16.10.1
```
### Warning about below

It is rare that fabric needs to be used beyond testing. But there may be use cases where direct control is required.

## Quick fabric lesson

```
fab -l gives list of fabric commands
fab build_xap builds xap rpm using current version
fab build_odphook:branch=developn-1 build odphook rpm using previous version
fab build_odphook:branch=developn-1,sha=adbcdefg build odphook n-1 but use a different sha as head
fab update_xaprepo
```
## N-1 and sha explanation
```
In most cases you don't need to specify the branch. It is needed if a n-1 build needs to be updated for bug fixes. This is the use case for specifying the branch. The sha is used when you don't want the head. Keep in mind that the version is based on the branch. So if it is needed to build n-1 at a specific sha. The branch and sha needs to be defined.
```
